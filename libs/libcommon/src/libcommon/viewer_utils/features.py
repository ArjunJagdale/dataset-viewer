# SPDX-License-Identifier: Apache-2.0
# Copyright 2022 The HuggingFace Authors.

import json
import logging
import os
from io import BytesIO
from typing import Any, Optional, Union
from zlib import adler32

import datasets.config
import numpy as np
import pdfplumber
import soundfile  # type: ignore
from datasets import (
    Array2D,
    Array3D,
    Array4D,
    Array5D,
    Audio,
    ClassLabel,
    Features,
    Image,
    LargeList,
    List,
    Pdf,
    Translation,
    TranslationVariableLanguages,
    Value,
    Video,
)
from datasets.features.features import FeatureType, _visit
from PIL import Image as PILImage

from libcommon.dtos import FeatureItem
from libcommon.storage_client import StorageClient
from libcommon.viewer_utils.asset import (
    SUPPORTED_AUDIO_EXTENSIONS,
    create_audio_file,
    create_image_file,
    create_pdf_file,
    create_video_file,
)

AUDIO_FILE_MAGIC_NUMBERS: dict[str, Any] = {
    ".wav": [(b"\x52\x49\x46\x46", 0), (b"\x57\x41\x56\x45", 8)],  # AND: (magic_number, start)
    ".mp3": (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\x49\x44\x33"),  # OR
}

logging.getLogger("pdfminer").setLevel(logging.ERROR)


def append_hash_suffix(string: str, json_path: Optional[list[Union[str, int]]] = None) -> str:
    """
    Hash the json path to a string.
    Details:
    - no suffix if the list is empty
    - converted to hexadecimal to make the hash shorter
    - the 0x prefix is removed

    Args:
        string (`str`): The string to append the hash to.
        json_path (`list(str|int)`): the json path, which is a list of keys and indices
    Returns:
        `str`: the string suffixed with the hash of the json path
    """
    return f"{string}-{hex(adler32(json.dumps(json_path).encode()))[2:]}" if json_path else string


def image(
    dataset: str,
    revision: str,
    config: str,
    split: str,
    row_idx: int,
    value: Any,
    featureName: str,
    storage_client: StorageClient,
    json_path: Optional[list[Union[str, int]]] = None,
) -> Any:
    if value is None:
        return None
    if isinstance(value, dict) and value.get("bytes"):
        value = PILImage.open(BytesIO(value["bytes"]))
    elif isinstance(value, bytes):
        value = PILImage.open(BytesIO(value))
    elif (
        isinstance(value, dict)
        and "path" in value
        and isinstance(value["path"], str)
        and os.path.exists(value["path"])
    ):
        value = PILImage.open(value["path"])
    if not isinstance(value, PILImage.Image):
        raise TypeError(
            "Image cell must be a PIL image or an encoded dict of an image, "
            f"but got {str(value)[:300]}{'...' if len(str(value)) > 300 else ''}"
        )
    # attempt to generate one of the supported formats; if unsuccessful, throw an error
    for ext, format in [(".jpg", "JPEG"), (".png", "PNG")]:
        try:
            return create_image_file(
                dataset=dataset,
                revision=revision,
                config=config,
                split=split,
                row_idx=row_idx,
                column=featureName,
                filename=f"{append_hash_suffix('image', json_path)}{ext}",
                image=value,
                format=format,
                storage_client=storage_client,
            )
        except OSError:
            # if wrong format, try the next one, see https://github.com/huggingface/dataset-viewer/issues/191
            #  OSError: cannot write mode P as JPEG
            #  OSError: cannot write mode RGBA as JPEG
            continue
    raise ValueError("Image cannot be written as JPEG or PNG")


def audio(
    dataset: str,
    revision: str,
    config: str,
    split: str,
    row_idx: int,
    value: Any,
    featureName: str,
    storage_client: StorageClient,
    json_path: Optional[list[Union[str, int]]] = None,
) -> Any:
    from datasets.features._torchcodec import AudioDecoder

    if value is None:
        return None
    if not isinstance(value, (dict, AudioDecoder)):
        raise TypeError(
            "Audio cell must be an encoded dict of an audio sample or a torchcodec AudioDecoder, "
            f"but got {str(value)[:300]}{'...' if len(str(value)) > 300 else ''}"
        )
    audio_file_extension = get_audio_file_extension(value)
    audio_file_bytes = get_audio_file_bytes(value)
    if not audio_file_extension:
        audio_file_extension = infer_audio_file_extension(audio_file_bytes)
    # convert to wav if the audio file extension is not supported
    target_audio_file_extension = (
        audio_file_extension if audio_file_extension in SUPPORTED_AUDIO_EXTENSIONS else ".wav"
    )
    # this function can raise, we don't catch it
    return create_audio_file(
        dataset=dataset,
        revision=revision,
        config=config,
        split=split,
        row_idx=row_idx,
        column=featureName,
        audio_file_bytes=audio_file_bytes,
        audio_file_extension=audio_file_extension,
        storage_client=storage_client,
        filename=f"{append_hash_suffix('audio', json_path)}{target_audio_file_extension}",
    )


def get_audio_file_bytes(value: Any) -> bytes:
    from datasets.features._torchcodec import AudioDecoder

    if isinstance(value, dict) and "bytes" in value and isinstance(value["bytes"], bytes):
        audio_file_bytes = value["bytes"]
    elif (
        isinstance(value, dict)
        and "path" in value
        and isinstance(value["path"], str)
        and os.path.exists(value["path"])
    ):
        with open(value["path"], "rb") as f:
            audio_file_bytes = f.read()
    elif isinstance(value, AudioDecoder):
        if (
            hasattr(value, "_hf_encoded")
            and isinstance(value._hf_encoded, dict)
            and "bytes" in value._hf_encoded
            and isinstance(value._hf_encoded["bytes"], bytes)
        ):
            audio_file_bytes = value._hf_encoded["bytes"]
        else:
            _array = value["array"]
            _sampling_rate = value["sampling_rate"]
            if isinstance(_array, np.ndarray) and isinstance(_sampling_rate, int):
                buffer = BytesIO()
                soundfile.write(buffer, _array, _sampling_rate, format="wav")
                audio_file_bytes = buffer.getvalue()
    else:
        raise ValueError(
            "An audio sample should have 'path' and 'bytes' (or 'array' and 'sampling_rate') but got"
            f" {', '.join(value)}."
        )
    return audio_file_bytes


def get_audio_file_extension(value: Any) -> Optional[str]:
    from datasets.features._torchcodec import AudioDecoder

    if isinstance(value, dict) and "path" in value and isinstance(value["path"], str):
        # .split("::")[0] for chained URLs like zip://audio.wav::https://foo.bar/data.zip
        # It might be "" for audio files downloaded from the Hub: make it None
        audio_file_extension = os.path.splitext(value["path"].split("::")[0])[1] or None
    elif isinstance(value, AudioDecoder):
        if (
            hasattr(value, "_hf_encoded")
            and isinstance(value._hf_encoded, dict)
            and "path" in value._hf_encoded
            and isinstance(value._hf_encoded["path"], str)
        ):
            # .split("::")[0] for chained URLs like zip://audio.wav::https://foo.bar/data.zip
            # It might be "" for audio files downloaded from the Hub: make it None
            audio_file_extension = os.path.splitext(value._hf_encoded["path"].split("::")[0])[1] or None
        else:
            audio_file_extension = ".wav"
    else:
        raise ValueError(
            "An audio sample should have 'path' and 'bytes' (or be an AudioDecoder) but got" f" {', '.join(value)}."
        )
    return audio_file_extension


def infer_audio_file_extension(audio_file_bytes: bytes) -> Optional[str]:
    for audio_file_extension, magic_numbers in AUDIO_FILE_MAGIC_NUMBERS.items():
        if isinstance(magic_numbers, list):
            if all(audio_file_bytes.startswith(magic_number, start) for magic_number, start in magic_numbers):
                return audio_file_extension
        else:
            if audio_file_bytes.startswith(magic_numbers):
                return audio_file_extension
    return None


def video(
    dataset: str,
    revision: str,
    config: str,
    split: str,
    row_idx: int,
    value: Any,
    featureName: str,
    storage_client: StorageClient,
    json_path: Optional[list[Union[str, int]]] = None,
) -> Any:
    if datasets.config.TORCHVISION_AVAILABLE:
        from torchvision.io import VideoReader  # type: ignore

    else:
        VideoReader = None

    if value is None:
        return None
    if (
        VideoReader
        and isinstance(value, VideoReader)
        and hasattr(value, "_hf_encoded")
        and isinstance(value._hf_encoded, dict)
    ):
        value = value._hf_encoded  # `datasets` patches `torchvision` to store the encoded data here
    elif isinstance(value, dict):
        value = {"path": value.get("path"), "bytes": value["bytes"]}
    elif isinstance(value, bytes):
        value = {"path": None, "bytes": value}
    elif isinstance(value, str):
        value = {"path": value, "bytes": None}

    if not (isinstance(value, dict) and "path" in value and "bytes" in value):
        raise TypeError(
            "Video cell must be an encoded dict of a video, "
            f"but got {str(value)[:300]}{'...' if len(str(value)) > 300 else ''}"
        )

    video_file_extension = get_video_file_extension(value)
    return create_video_file(
        dataset=dataset,
        revision=revision,
        config=config,
        split=split,
        row_idx=row_idx,
        column=featureName,
        filename=f"{append_hash_suffix('video', json_path)}{video_file_extension}",
        encoded_video=value,
        storage_client=storage_client,
    )


def get_video_file_extension(value: Any) -> str:
    if "path" in value and isinstance(value["path"], str):
        # .split("::")[0] for chained URLs like zip://audio.wav::https://foo.bar/data.zip
        video_file_extension = os.path.splitext(value["path"].split("::")[0])[1]
        if not video_file_extension:
            raise ValueError(
                "A video sample should have a 'path' with a valid file name nd extension, but got"
                f" {', '.join(value['path'])}."
            )
    else:
        raise ValueError("A video sample should have 'path' and 'bytes' but got" f" {', '.join(value)}.")
    return video_file_extension


def pdf(
    dataset: str,
    revision: str,
    config: str,
    split: str,
    row_idx: int,
    value: Any,
    featureName: str,
    storage_client: StorageClient,
    json_path: Optional[list[Union[str, int]]] = None,
) -> Any:
    if value is None:
        return None
    if isinstance(value, dict) and value.get("bytes"):
        value = pdfplumber.open(BytesIO(value["bytes"]))
    elif isinstance(value, bytes):
        value = pdfplumber.open(BytesIO(value))
    elif (
        isinstance(value, dict)
        and "path" in value
        and isinstance(value["path"], str)
        and os.path.exists(value["path"])
    ):
        value = pdfplumber.open(value["path"])

    if not isinstance(value, pdfplumber.pdf.PDF):
        raise TypeError(
            "PDF cell must be a pdfplumber.pdf.PDF object or an encoded dict of a PDF, "
            f"but got {str(value)[:300]}{'...' if len(str(value)) > 300 else ''}"
        )

    # this function can raise, we don't catch it
    return create_pdf_file(
        dataset=dataset,
        revision=revision,
        config=config,
        split=split,
        row_idx=row_idx,
        column=featureName,
        pdf=value,
        storage_client=storage_client,
        filename=f"{append_hash_suffix('document', json_path)}.pdf",
    )


def get_cell_value(
    dataset: str,
    revision: str,
    config: str,
    split: str,
    row_idx: int,
    cell: Any,
    featureName: str,
    fieldType: Any,
    storage_client: StorageClient,
    json_path: Optional[list[Union[str, int]]] = None,
) -> Any:
    # always allow None values in the cells
    if cell is None:
        return cell
    if isinstance(fieldType, Image):
        return image(
            dataset=dataset,
            revision=revision,
            config=config,
            split=split,
            row_idx=row_idx,
            value=cell,
            featureName=featureName,
            storage_client=storage_client,
            json_path=json_path,
        )
    elif isinstance(fieldType, Audio):
        return audio(
            dataset=dataset,
            revision=revision,
            config=config,
            split=split,
            row_idx=row_idx,
            value=cell,
            featureName=featureName,
            storage_client=storage_client,
            json_path=json_path,
        )
    elif isinstance(fieldType, Video):
        return video(
            dataset=dataset,
            revision=revision,
            config=config,
            split=split,
            row_idx=row_idx,
            value=cell,
            featureName=featureName,
            storage_client=storage_client,
            json_path=json_path,
        )
    elif isinstance(fieldType, Pdf):
        return pdf(
            dataset=dataset,
            revision=revision,
            config=config,
            split=split,
            row_idx=row_idx,
            value=cell,
            featureName=featureName,
            storage_client=storage_client,
            json_path=json_path,
        )
    elif isinstance(fieldType, list):
        if not isinstance(cell, list):
            raise TypeError("list cell must be a list.")
        if len(fieldType) != 1:
            raise TypeError("the feature type should be a 1-element list.")
        subFieldType = fieldType[0]
        return [
            get_cell_value(
                dataset=dataset,
                revision=revision,
                config=config,
                split=split,
                row_idx=row_idx,
                cell=subCell,
                featureName=featureName,
                fieldType=subFieldType,
                storage_client=storage_client,
                json_path=json_path + [idx] if json_path else [idx],
            )
            for (idx, subCell) in enumerate(cell)
        ]
    elif isinstance(fieldType, LargeList):
        if not isinstance(cell, list):
            raise TypeError("list cell must be a list.")
        subFieldType = fieldType.feature
        return [
            get_cell_value(
                dataset=dataset,
                revision=revision,
                config=config,
                split=split,
                row_idx=row_idx,
                cell=subCell,
                featureName=featureName,
                fieldType=subFieldType,
                storage_client=storage_client,
                json_path=json_path + [idx] if json_path else [idx],
            )
            for (idx, subCell) in enumerate(cell)
        ]
    elif isinstance(fieldType, List):
        if not isinstance(cell, list):
            raise TypeError("list cell must be a list.")
        if fieldType.length >= 0 and len(cell) != fieldType.length:
            raise TypeError("the cell length should be the same as the List length.")
        return [
            get_cell_value(
                dataset=dataset,
                revision=revision,
                config=config,
                split=split,
                row_idx=row_idx,
                cell=subCell,
                featureName=featureName,
                fieldType=fieldType.feature,
                storage_client=storage_client,
                json_path=json_path + [idx] if json_path else [idx],
            )
            for (idx, subCell) in enumerate(cell)
        ]

    elif isinstance(fieldType, dict):
        if not isinstance(cell, dict):
            raise TypeError("dict cell must be a dict.")
        return {
            key: get_cell_value(
                dataset=dataset,
                revision=revision,
                config=config,
                split=split,
                row_idx=row_idx,
                cell=subCell,
                featureName=featureName,
                fieldType=fieldType[key],
                storage_client=storage_client,
                json_path=json_path + [key] if json_path else [key],
            )
            for (key, subCell) in cell.items()
        }
    elif isinstance(
        fieldType,
        (
            Value,
            ClassLabel,
            Array2D,
            Array3D,
            Array4D,
            Array5D,
            Translation,
            TranslationVariableLanguages,
        ),
    ):
        return cell
    else:
        raise TypeError("could not determine the type of the data cell.")


# in JSON, dicts do not carry any order, so we need to return a list
#
# > An object is an *unordered* collection of zero or more name/value pairs, where a name is a string and a value
#   is a string, number, boolean, null, object, or array.
# > An array is an *ordered* sequence of zero or more values.
# > The terms "object" and "array" come from the conventions of JavaScript.
# from https://stackoverflow.com/a/7214312/7351594 / https://www.rfc-editor.org/rfc/rfc7159.html
def to_features_list(features: Features) -> list[FeatureItem]:
    features_dict = features.to_dict()
    return [
        {
            "feature_idx": idx,
            "name": name,
            "type": features_dict[name],
        }
        for idx, name in enumerate(features)
    ]


def get_supported_unsupported_columns(
    features: Features,
    unsupported_features: list[FeatureType] = [],
) -> tuple[list[str], list[str]]:
    supported_columns, unsupported_columns = [], []

    for column, feature in features.items():
        str_column = str(column)
        supported = True

        def classify(feature: FeatureType) -> None:
            nonlocal supported
            for unsupported_feature in unsupported_features:
                if type(unsupported_feature) == type(feature) == Value:
                    if unsupported_feature.dtype == feature.dtype:
                        supported = False
                elif type(unsupported_feature) == type(feature):
                    supported = False

        _visit(feature, classify)
        if supported:
            supported_columns.append(str_column)
        else:
            unsupported_columns.append(str_column)
    return supported_columns, unsupported_columns

# Search text in a dataset

The dataset viewer provides a `/search` endpoint for searching words in a dataset.

<Tip warning={true}>
  Currently, only <a href="./parquet">datasets with Parquet exports</a>
  are supported so the dataset viewer can index the contents and run the search without
  downloading the whole dataset.
</Tip>

This guide shows you how to use the dataset viewer's `/search` endpoint to search for a query string.
Feel free to also try it out with [ReDoc](https://redocly.github.io/redoc/?url=https://datasets-server.huggingface.co/openapi.json#operation/searchRows).

The text is searched in the columns of type `string`, even if the values are nested in a dictionary.

<Tip>

We use [DuckDB](https://duckdb.org/docs/) for [full text search](https://duckdb.org/docs/extensions/full_text_search.html) with the `BM25` (Best Match 25) algorithm. `BM25` is a ranking algorithm for information retrieval and search engines that determines a document’s relevance to a given query and ranks documents based on their relevance scores.
[`Porter` stemmer](https://tartarus.org/martin/PorterStemmer/) (which assumes English text) is used to reduce words to their root or base form, known as the stem. This process, called stemming, involves removing suffixes and prefixes from words to identify their core meaning. The purpose of a stemmer is to improve search accuracy and efficiency by ensuring that different forms of a word are recognized as the same term.

</Tip>

The `/search` endpoint accepts five query parameters:

- `dataset`: the dataset name, for example `nyu-mll/glue` or `mozilla-foundation/common_voice_10_0`
- `config`: the subset name, for example `cola`
- `split`: the split name, for example `train`
- `query`: the text to search
- `offset`: the offset of the slice, for example `150`
- `length`: the length of the slice, for example `10` (maximum: `100`)

For example, let's search for the text `"dog"` in the `train` split of the `SelfRC` subset of the `ibm/duorc` dataset, restricting the results to the slice 150-151:

<inferencesnippet>
<python>
```python
import requests
headers = {"Authorization": f"Bearer {API_TOKEN}"}
API_URL = "https://datasets-server.huggingface.co/search?dataset=ibm/duorc&config=SelfRC&split=train&query=dog&offset=150&length=2"
def query():
    response = requests.get(API_URL, headers=headers)
    return response.json()
data = query()
```
</python>
<js>
```js
import fetch from "node-fetch";
async function query(data) {
    const response = await fetch(
        "https://datasets-server.huggingface.co/search?dataset=ibm/duorc&config=SelfRC&split=train&query=dog&offset=150&length=2",
        {
            headers: { Authorization: `Bearer ${API_TOKEN}` },
            method: "GET"
        }
    );
    const result = await response.json();
    return result;
}
query().then((response) => {
    console.log(JSON.stringify(response));
});
```
</js>
<curl>
```curl
curl https://datasets-server.huggingface.co/search?dataset=ibm/duorc&config=SelfRC&split=train&query=dog&offset=150&length=2 \
        -X GET \
        -H "Authorization: Bearer ${API_TOKEN}"
```
</curl>
</inferencesnippet>

The endpoint response is a JSON containing two keys (same format as [`/rows`](./rows)):

- The [`features`](https://huggingface.co/docs/datasets/about_dataset_features) of a dataset, including the column's name and data type.
- The slice of `rows` of a dataset and the content contained in each column of a specific row.

The rows are ordered by the row index, and the text strings matching the query are not highlighted.

For example, here are the `features` and the slice 150-151 of matching `rows` of the `ibm/duorc`/`SelfRC` train split for the query `dog`:

```json
{
  "features": [
    {
      "feature_idx": 0,
      "name": "plot_id",
      "type": { "dtype": "string", "_type": "Value" }
    },
    {
      "feature_idx": 1,
      "name": "plot",
      "type": { "dtype": "string", "_type": "Value" }
    },
    {
      "feature_idx": 2,
      "name": "title",
      "type": { "dtype": "string", "_type": "Value" }
    },
    {
      "feature_idx": 3,
      "name": "question_id",
      "type": { "dtype": "string", "_type": "Value" }
    },
    {
      "feature_idx": 4,
      "name": "question",
      "type": { "dtype": "string", "_type": "Value" }
    },
    {
      "feature_idx": 5,
      "name": "answers",
      "type": {
        "feature": { "dtype": "string", "_type": "Value" },
        "_type": "List"
      }
    },
    {
      "feature_idx": 6,
      "name": "no_answer",
      "type": { "dtype": "bool", "_type": "Value" }
    }
  ],
  "rows": [
    {
      "row_idx": 1561,
      "row": {
        "plot_id": "/m/014bjk",
        "plot": "The film begins with clips that track a telephone call between London and Geneva, where a university student and part-time model, Valentine Dussault (IrÃ¨ne Jacob), is talking to her emotionally infantile and possessive boyfriend. During her work as a model she poses for a chewing-gum campaign and during the photo shoot the photographer asks her to look very sad. While walking back home, Auguste, a neighbour of Valentine's, drops a set of books, notices that a particular chapter of the Criminal Code opened at random, and concentrates on that passage. As she drives back to her apartment, Valentine is distracted while adjusting the radio and accidentally hits a dog. She tracks down the owner, a reclusive retired judge, Joseph Kern (Jean-Louis Trintignant). He seems unconcerned by the accident or the injuries sustained by Rita, his dog. Valentine takes Rita to a veterinarian, where she learns that Rita is pregnant. Valentine takes the dog home. Later, money is delivered to her apartment from an unnamed sender.\nWhilst Valentine is walking Rita the next day the dog runs away and Valentine eventually finds her back at Kern's house. She asks and he confirms that the money sent to her came from him, for the vet bill. He then tells Valentine she can have the dog. A short time later Valentine finds Kern eavesdropping on his neighbours' private telephone conversations. The judge challenges Valentine to go tell the neighbours and initially she goes to do so. She visits the neighbours' house, which appears, on the surface, to contain a contented nuclear family, causing her to change her mind about exposing their secrets. She returns to Kern's house and Kern tells her that it would make no difference if she denounced him for his spying because the people's lives he listens to would eventually turn into hell anyway. She leaves saying that she feels nothing but pity for him.\nWhilst visiting Kern, Valentine hears a phone conversation between her (unbeknownst to her) neighbour, Auguste, and his girlfriend, Karin (Frederique Feder). They discuss if they should go bowling. Valentine covers her ears but from the very little she hears she concludes that they love each other. Kern disagrees. That evening Valentine is alone at home and hopes that her boyfriend will call, but it is the photographer who calls, saying that her billboard was set up that evening and asks her to join them bowling to celebrate. Later, Auguste takes his exam and passes it and becomes a judge. Karin asks if he was asked any questions regarding the article that was open when he dropped his books. Auguste says yes. Karin gives him a fancy fountain pen as a gift and he wonders what the first judgment he signs with it will be. That evening, Kern writes a series of letters to his neighbours and the court confessing his activities, and the community files a class action. Later, at the law courts, he sees Karin make the acquaintance of and begin to flirt with another man. Earlier, Auguste had missed a call from Karin and tried to call her back but got no answer.\nValentine reads the news about a retired judge who spied on his neighbours and rushes to Kern's house to tell him that she did not report on him. He confesses that he turned himself in, just to see what she would do. He asks her in and shows her that Rita has had seven puppies. He tells her that in their last conversation when she spoke about pity he later realized that she really meant disgust. He ponders about the reasons why people obey laws and concludes that often it is more on selfish grounds and from fear than about obeying the law or being decent. It is his birthday and he offers her pear brandy for a toast. During their conversation he reminisces about a sailor he acquitted a long time ago, only later realizing he had made a mistake, and that the man was guilty. However, the man later married, had children and grandchildren and lives peacefully and happy. Valentine says that he did what he had to do, but Kern wonders how many other people that he acquitted or condemned might have seen a different life had he decided otherwise. Valentine tells Kern about her intended trip to England for a modeling job and to visit her boyfriend. Kern suggests that she take the ferry.\nAuguste has been unable to reach Karin since graduation so he goes to her place and sees her having sex with another man. Distraught, he leaves. Later, Auguste sees Karin and her new boyfriend in a restaurant. He gets her attention by tapping on the restaurant window with the pen she gave him. But when she rushes outside, he hides from her. In a temper, he ties his dog by a quayside and abandons him.\nKarin runs a service providing personalised weather information to travelers by telephone. Kern calls and enquires about the weather in the English Channel for the time when Valentine will be traveling to England. Karin states that she expects the weather to be perfect and reveals that she is about to take a trip there (with her new boyfriend who owns a yacht).\nThe day before Valentine leaves, she invites Kern to a fashion show where she is modeling. After the show they speak about the dream Kern had about her, where he saw her at the age of 50 and happy with an unidentified man. The conversation then turns to Kern and the reasons why he disliked Karin. Kern reveals that before becoming a judge, he was in love with a woman very much like Karin, who betrayed him for another man. While preparing for his exam, he once went to the same theatre where the fashion show took place and he accidentally dropped one of his books. When he picked it up, Kern studied the chapter where the book accidentally opened, which turned out to be the crucial question at his examination. After his girlfriend left him, he followed her across the English Channel but never saw her again, because she died in an accident. Later, he was assigned to judge a case where the defendant was the same man who took his girlfriend from him. Despite this connection, Kern did not recuse himself from the case and found the man guilty. He tells Valentine the judgment was entirely legal but also that he subsequently requested early retirement.\nValentine boards the ferry to England. Auguste is also on the ferry, clutching the dog he had temporarily abandoned. Although living in the same neighborhood and nearly crossing paths many times, the two have still never met. Suddenly a storm rises and sinks both the ferry and the boat with Karin and her boyfriend. Only seven survivors are pulled from the ferry: the main characters from the first two films of the trilogy, Julie and Olivier from Blue, Karol and Dominique from White, and Valentine and Auguste, who meet for the first time, as well as an English bartender named Stephen Killian. As in the previous films, the film's final sequence shows a character crying - in this case, the judge - but the final image replicates the iconic chewing-gum poster of Valentine, but this time with real emotion showing on her face.",
        "title": "Three Colors: Red",
        "question_id": "7c583513-0b7f-ddb3-be43-64befc7e90cc",
        "question": "Where is Valentine going on her trip?",
        "answers": ["England."],
        "no_answer": false
      },
      "truncated_cells": []
    },
    {
      "row_idx": 1562,
      "row": {
        "plot_id": "/m/014bjk",
        "plot": "The film begins with clips that track a telephone call between London and Geneva, where a university student and part-time model, Valentine Dussault (IrÃ¨ne Jacob), is talking to her emotionally infantile and possessive boyfriend. During her work as a model she poses for a chewing-gum campaign and during the photo shoot the photographer asks her to look very sad. While walking back home, Auguste, a neighbour of Valentine's, drops a set of books, notices that a particular chapter of the Criminal Code opened at random, and concentrates on that passage. As she drives back to her apartment, Valentine is distracted while adjusting the radio and accidentally hits a dog. She tracks down the owner, a reclusive retired judge, Joseph Kern (Jean-Louis Trintignant). He seems unconcerned by the accident or the injuries sustained by Rita, his dog. Valentine takes Rita to a veterinarian, where she learns that Rita is pregnant. Valentine takes the dog home. Later, money is delivered to her apartment from an unnamed sender.\nWhilst Valentine is walking Rita the next day the dog runs away and Valentine eventually finds her back at Kern's house. She asks and he confirms that the money sent to her came from him, for the vet bill. He then tells Valentine she can have the dog. A short time later Valentine finds Kern eavesdropping on his neighbours' private telephone conversations. The judge challenges Valentine to go tell the neighbours and initially she goes to do so. She visits the neighbours' house, which appears, on the surface, to contain a contented nuclear family, causing her to change her mind about exposing their secrets. She returns to Kern's house and Kern tells her that it would make no difference if she denounced him for his spying because the people's lives he listens to would eventually turn into hell anyway. She leaves saying that she feels nothing but pity for him.\nWhilst visiting Kern, Valentine hears a phone conversation between her (unbeknownst to her) neighbour, Auguste, and his girlfriend, Karin (Frederique Feder). They discuss if they should go bowling. Valentine covers her ears but from the very little she hears she concludes that they love each other. Kern disagrees. That evening Valentine is alone at home and hopes that her boyfriend will call, but it is the photographer who calls, saying that her billboard was set up that evening and asks her to join them bowling to celebrate. Later, Auguste takes his exam and passes it and becomes a judge. Karin asks if he was asked any questions regarding the article that was open when he dropped his books. Auguste says yes. Karin gives him a fancy fountain pen as a gift and he wonders what the first judgment he signs with it will be. That evening, Kern writes a series of letters to his neighbours and the court confessing his activities, and the community files a class action. Later, at the law courts, he sees Karin make the acquaintance of and begin to flirt with another man. Earlier, Auguste had missed a call from Karin and tried to call her back but got no answer.\nValentine reads the news about a retired judge who spied on his neighbours and rushes to Kern's house to tell him that she did not report on him. He confesses that he turned himself in, just to see what she would do. He asks her in and shows her that Rita has had seven puppies. He tells her that in their last conversation when she spoke about pity he later realized that she really meant disgust. He ponders about the reasons why people obey laws and concludes that often it is more on selfish grounds and from fear than about obeying the law or being decent. It is his birthday and he offers her pear brandy for a toast. During their conversation he reminisces about a sailor he acquitted a long time ago, only later realizing he had made a mistake, and that the man was guilty. However, the man later married, had children and grandchildren and lives peacefully and happy. Valentine says that he did what he had to do, but Kern wonders how many other people that he acquitted or condemned might have seen a different life had he decided otherwise. Valentine tells Kern about her intended trip to England for a modeling job and to visit her boyfriend. Kern suggests that she take the ferry.\nAuguste has been unable to reach Karin since graduation so he goes to her place and sees her having sex with another man. Distraught, he leaves. Later, Auguste sees Karin and her new boyfriend in a restaurant. He gets her attention by tapping on the restaurant window with the pen she gave him. But when she rushes outside, he hides from her. In a temper, he ties his dog by a quayside and abandons him.\nKarin runs a service providing personalised weather information to travelers by telephone. Kern calls and enquires about the weather in the English Channel for the time when Valentine will be traveling to England. Karin states that she expects the weather to be perfect and reveals that she is about to take a trip there (with her new boyfriend who owns a yacht).\nThe day before Valentine leaves, she invites Kern to a fashion show where she is modeling. After the show they speak about the dream Kern had about her, where he saw her at the age of 50 and happy with an unidentified man. The conversation then turns to Kern and the reasons why he disliked Karin. Kern reveals that before becoming a judge, he was in love with a woman very much like Karin, who betrayed him for another man. While preparing for his exam, he once went to the same theatre where the fashion show took place and he accidentally dropped one of his books. When he picked it up, Kern studied the chapter where the book accidentally opened, which turned out to be the crucial question at his examination. After his girlfriend left him, he followed her across the English Channel but never saw her again, because she died in an accident. Later, he was assigned to judge a case where the defendant was the same man who took his girlfriend from him. Despite this connection, Kern did not recuse himself from the case and found the man guilty. He tells Valentine the judgment was entirely legal but also that he subsequently requested early retirement.\nValentine boards the ferry to England. Auguste is also on the ferry, clutching the dog he had temporarily abandoned. Although living in the same neighborhood and nearly crossing paths many times, the two have still never met. Suddenly a storm rises and sinks both the ferry and the boat with Karin and her boyfriend. Only seven survivors are pulled from the ferry: the main characters from the first two films of the trilogy, Julie and Olivier from Blue, Karol and Dominique from White, and Valentine and Auguste, who meet for the first time, as well as an English bartender named Stephen Killian. As in the previous films, the film's final sequence shows a character crying - in this case, the judge - but the final image replicates the iconic chewing-gum poster of Valentine, but this time with real emotion showing on her face.",
        "title": "Three Colors: Red",
        "question_id": "80becb22-908d-84bc-3a5f-00b620d551bc",
        "question": "What was the profession of the dog's owner?",
        "answers": ["Retired Judge"],
        "no_answer": false
      },
      "truncated_cells": []
    }
  ],
  "num_rows_total": 5247,
  "num_rows_per_page": 100,
  "partial": false
}
```

If the result has `partial: true` it means that the search couldn't be run on the full dataset because it's too big.

Indeed, the indexing for `/search` can be partial if the dataset is bigger than 5GB. In that case, it only uses the first 5GB.


## Truncated responses

Unlike `/first-rows`, there is currently no truncation in `/search`.
The `truncated_cells` field is still there but is always empty.

# This file takes the training data and tokenizes it so that the model can train on it
import nltk
import pandas as pd
from nltk.tokenize import word_tokenize

nltk.download("punkt_tab")

# comment like "I'm not expecting NVDA to hit 12.5 tomorrow"
# Tokenizer splits it into "I ' m not expect ing NV DA to hit 12 . 5 tom orrow"
# In the training data, the classifier will see "NV" for the stock ticker, since it's the first piece of the ticker
# we want it to know the whole ticker is important, while still preserving the functionality of the subtokenization
# So this script uses a B- token as the first part of a ticker, and then an I- token for each other piece of the valid token, and an O token for anything that isn't important
# So our original comment would look like this "I(O) '(O) m(O) not(O) expect(O) ing(O) NV(B-) DA(I-) to(O) hit(O-) 12(B-) .(I-) 5(I-) tom(B-) orrow(I-)"
# This makes it so the model can train on subtokens (improving accuracy on really nasty and confusing text) while preserving the original tokens in their entirety (so it doesn't fuck up the classifications)
# The bio tagger file splits it all up into tokens, and classifier file puts it all together and trains the model on it


# Cleans and standarizes data, and then splits it into tokens using the nltk tokenizer
def label_comment(comment, ticker, price, date):
    price = price.strip(" $")
    ticker = ticker.strip(" $")
    date = date.strip("[]")
    tokens = word_tokenize(comment)
    labels = ["O"] * len(tokens)

    def clean_token(token):
        return token.strip(".,!?$:/\\")

    def tag_entity(entity, tag):
        entity_tokens = word_tokenize(entity)
        for i in range(len(tokens) - len(entity_tokens) + 1):
            token_span_clean = [
                clean_token(t) for t in tokens[i : i + len(entity_tokens)]
            ]
            entity_tokens_clean = [clean_token(t) for t in entity_tokens]
            if token_span_clean == entity_tokens_clean:
                labels[i] = f"B-{tag}"
                for j in range(1, len(entity_tokens)):
                    labels[i + j] = f"I-{tag}"
                break

    tag_entity(ticker, "TICKER")
    tag_entity(price, "PRICE")
    tag_entity(date, "DATE")
    return tokens, labels


# Takes the tokenized data and returns it as an array
def generate_labeled_data():
    # file1 = pd.read_csv("pre_processing/prepped_stocks.csv")
    file2 = pd.read_csv(
        "NER_Classifier/regression_model_training_data.csv", usecols=range(5)
    )
    # combined_files = pd.concat([file1, file2], ignore_index=True)
    file2 = file2[file2["Label"].astype(float) == 1.0]
    # combined_files = combined_files[combined_files["Label"].astype(float) == 1.0]
    examples = []

    for _, row in file2.iterrows():
        tokens, labels = label_comment(
            row["Comment"], row["Stock"], row["Price"], row["Date"]
        )
        examples.append({"tokens": tokens, "ner_tags": labels})

    return examples

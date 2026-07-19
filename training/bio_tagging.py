# Takes the labeled training data and BIO-tags it so the NER model can train on it.
#
# A comment like "I'm not expecting NVDA to hit 12.5 tomorrow" gets split by the
# tokenizer into "I ' m not expect ing NV DA to hit 12 . 5 tom orrow". The classifier
# would only see "NV" as the start of the ticker, so we tag the first piece of an
# entity with B- and every following piece with I-, and everything else with O:
# "I(O) '(O) m(O) not(O) expect(O) ing(O) NV(B-) DA(I-) to(O) hit(O) 12(B-) .(I-) 5(I-) tom(B-) orrow(I-)"
# This lets the model train on subtokens (improving accuracy on really nasty text)
# while preserving the original tokens in their entirety.
import ssl
from pathlib import Path

import nltk
import pandas as pd
from nltk.tokenize import word_tokenize

ssl._create_default_https_context = ssl._create_unverified_context
nltk.download("punkt_tab")

DATA_FILE = Path(__file__).resolve().parent / "data" / "regression_model_training_data.csv"


# Cleans and standardizes data, then splits it into tokens using the nltk tokenizer
def label_comment(comment, ticker, price, date, optiontype):
    price = str(price).strip(" $")
    ticker = str(ticker).strip(" $")
    date = str(date).strip("[]")
    tokens = word_tokenize(comment)
    labels = ["O"] * len(tokens)

    def clean_token(token):
        return token.strip(".,!?$:/\\")

    def tag_entity(entity, tag):
        entity_tokens = word_tokenize(entity)
        if not entity_tokens:
            return
        entity_tokens_clean = [clean_token(t) for t in entity_tokens]
        for i in range(len(tokens) - len(entity_tokens) + 1):
            token_span_clean = [clean_token(t) for t in tokens[i : i + len(entity_tokens)]]
            if token_span_clean == entity_tokens_clean:
                labels[i] = f"B-{tag}"
                for j in range(1, len(entity_tokens)):
                    labels[i + j] = f"I-{tag}"
                break

    tag_entity(ticker, "TICKER")
    tag_entity(price, "STRIKE")
    tag_entity(date, "EXPIRY")
    tag_entity(optiontype, "OPTIONTYPE")
    return tokens, labels


# Reads the training CSV and returns the tokenized, tagged examples
def generate_labeled_data():
    file = pd.read_csv(
        DATA_FILE,
        usecols=["Comment", "Ticker", "Strike", "Expiry", "OptionType", "Label"],
    )
    examples = []
    for _, row in file.iterrows():
        tokens, labels = label_comment(
            str(row["Comment"]) if pd.notna(row["Comment"]) else "",
            str(row["Ticker"]) if pd.notna(row["Ticker"]) else "",
            str(row["Strike"]) if pd.notna(row["Strike"]) else "",
            str(row["Expiry"]) if pd.notna(row["Expiry"]) else "",
            str(row.get("OptionType", "")) if pd.notna(row.get("OptionType", "")) else "",
        )
        examples.append({"tokens": tokens, "ner_tags": labels})
    return examples

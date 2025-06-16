# This file takes the training data and tokenizes it so that the model can train on it
import ssl
import nltk
import pandas as pd
from nltk.tokenize import word_tokenize
ssl._create_default_https_context = ssl._create_unverified_context
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
        for i in range(len(tokens) - len(entity_tokens) + 1):
            token_span_clean = [clean_token(t) for t in tokens[i : i + len(entity_tokens)]]
            entity_tokens_clean = [clean_token(t) for t in entity_tokens]
            if token_span_clean == entity_tokens_clean:
                labels[i] = f"B-{tag}"
                for j in range(1, len(entity_tokens)):
                    labels[i + j] = f"I-{tag}"
                break
    tag_entity(ticker, "TICKER")
    tag_entity(price, "STRIKE")
    tag_entity(date, "EXPIRY")
    tag_entity(optiontype, "OPTIONTYPE")
    #tag_entity(quantity, "QUANTITY")
    #tag_entity(premium, "PREMIUM")
    return tokens, labels



# Takes the tokenized data and returns it as an array
def generate_labeled_data():
    file2 = pd.read_csv(
        "NER_Classifier/regression_model_training_data.csv", usecols=["Comment", "Ticker", "Strike", "Expiry", "OptionType", "Label"]
    )
    #file2 = file2[file2["Label"].astype(float).isin([0.0, 1.0, 2.0])]
    
    examples = []
    for _, row in file2.iterrows():
        tokens, labels = label_comment(
        str(row["Comment"]) if pd.notna(row["Comment"]) else "",
        str(row["Ticker"]) if pd.notna(row["Ticker"]) else "",
        str(row["Strike"]) if pd.notna(row["Strike"]) else "",
        str(row["Expiry"]) if pd.notna(row["Expiry"]) else "",
        str(row.get("OptionType", "")) if pd.notna(row.get("OptionType", "")) else "",
        #str(row.get("Quantity", "")) if pd.notna(row.get("Quantity", "")) else "",
        #str(row.get("Premium", "")) if pd.notna(row.get("Premium", "")) else "",
)

        examples.append({"tokens": tokens, "ner_tags": labels})
    return examples

#This file takes the training data and tokenizes it so that the model can train on it
from pathlib import Path
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
nltk.download('punkt_tab')

#Cleans and standarizes data, and then splits it into tokens using the nltk tokenizer
def label_comment(comment, ticker, price, date):
    price = price.strip(" $")
    ticker = ticker.strip(" $")
    date = date.strip("[]")
    tokens = word_tokenize(comment)
    labels = ['O'] * len(tokens)

    def clean_token(token):
        return token.strip('.,!?$:/\\')

    def tag_entity(entity, tag):
        entity_tokens = word_tokenize(entity)
        for i in range(len(tokens) - len(entity_tokens) + 1):
            token_span_clean = [clean_token(t) for t in tokens[i:i+len(entity_tokens)]]
            entity_tokens_clean = [clean_token(t) for t in entity_tokens]
            if token_span_clean == entity_tokens_clean:
                labels[i] = f'B-{tag}'
                for j in range(1, len(entity_tokens)):
                    labels[i+j] = f'I-{tag}'
                break

    tag_entity(ticker, 'TICKER')
    tag_entity(price, 'PRICE')
    tag_entity(date, 'DATE')
    return tokens, labels

#Takes the tokenized data and returns it as an array
def generate_labeled_data():
    file1 = pd.read_csv("pre_processing/prepped_stocks.csv")
    file2 = pd.read_csv("post_processing/regression_model_training_data.csv", usecols=range(5))
    combined_files = pd.concat([file1, file2], ignore_index=True)
    combined_files = combined_files[combined_files["Label"].astype(str).str.strip() == '1']
    examples = []

    for _, row in combined_files.iterrows():
        tokens, labels = label_comment(row['Comment'], row['Stock'], row['Price'], row['Date'])
        examples.append({"tokens": tokens, "ner_tags": labels})
    
    return examples

    
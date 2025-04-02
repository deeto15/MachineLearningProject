import string
import pandas as pd
import openai as OpenAI
import csv
import nltk
nltk.download('punkt_tab')
from nltk.tokenize import word_tokenize

print(nltk.data.path)

def label_comment(comment, ticker, price, date):
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
    return list(zip(tokens, labels))

with open('pre_processing\prepped_stocks.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    with open('labeled_data.txt', 'w', encoding='utf-8') as out:
        for row in reader:
            if row.get('label', row.get('Label', '0')) != '1':
                continue
            comment = row['Comment']
            ticker = row['Stock']
            price = row['Price']
            date = row['Date'].strip('[]').strip()
            labeled = label_comment(comment, ticker, price, date)
            for token, tag in labeled:
                out.write(f'{token} {tag}\n')
            out.write('\n')

def generate_synthetic_data(openai_key):
    return
    
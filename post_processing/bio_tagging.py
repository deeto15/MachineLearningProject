import pandas as pd
import openai as OpenAI
import nltk
nltk.download('punkt_tab')
from nltk.tokenize import word_tokenize

file1 = pd.read_csv("pre_processing/prepped_stocks.csv")
file2 = pd.read_csv("post_processing/ner_results.csv", usecols=range(5))
combined_files = pd.concat([file1, file2], ignore_index=True)
combined_files = combined_files[combined_files["Label"].astype(str).str.strip() == '1']
nan_rows = combined_files[combined_files['Price'].isna()]
print(nan_rows)
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
    return list(zip(tokens, labels))

with open('labeled_data.txt', 'w', encoding='utf-8') as out:
    for _, row in combined_files.iterrows():
        if row['Label'] != 1:
            continue
        comment = row['Comment']
        ticker = row['Stock']
        price = row['Price']
        date = row['Date'].strip('[]').strip()
        labeled = label_comment(comment, ticker, price, date)
        for token, tag in labeled:
            out.write(f'{token} {tag}\n')
        out.write('\n')

    
import json
from pathlib import Path
import re
import spacy
from stock_cap_processor import filter_stocks
import pandas as pd
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions.txt"

def extract_dates(comment):
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(comment)
    date = [ent for ent in doc.ents if ent.label_ == "DATE"]
    if date:
        return date
    else:
        return None

def extract_prices(comment):
    pattern = r'(?:^|(?<![\d.]))(\$?\d+\.\d{1,2})(?!\.\d)(?=$|[^\d.])'
    match = re.search(pattern, comment)
    if match:
        return match.group()
    else:
        return None

def extract_stocks(comment):
    stock_tickers = filter_stocks()
    for stock_ticker in stock_tickers:
        if stock_ticker in comment:
            return stock_ticker
        
def save_to_excel(comment, stock, price, date, file):
    df = pd.DataFrame([[comment, stock, price, date]], columns=["Comment", "Stock", "Price", "Date"])
    df.to_csv(file, mode='a', header=not pd.io.common.file_exists(file), index=False)

accepted_comments = {}
i = 0
with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        comment = json.loads(line)
        stock = extract_stocks(comment['title'])
        price = extract_prices(comment['title'])
        date = extract_dates(comment['title'])
        if stock != None and price != None and date != None:
            save_to_excel(comment, stock, price, date, "prepped_stocks.csv")
        else:
            if i < 5000:
                save_to_excel(comment, stock, price, date, "unprepped_stocks.csv")
                i+=1


        
                 
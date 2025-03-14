import json
import re
import os
import spacy
from file_read_backwards import FileReadBackwards
from stock_cap_processor import filter_stocks
file_path = r"C:\Users\Kendall Eberly\Downloads\wallstreetbets_submissions\wallstreetbets_submissions"

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

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        comment = json.loads(line)
        stock = extract_stocks(comment['title'])
        price = extract_prices(comment['title'])
        date = extract_dates(comment['title'])
        if stock != None and price != None and date != None:
            print(comment['title'])
            print(stock, price, date)
                 
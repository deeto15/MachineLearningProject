import csv
import json
from pathlib import Path
import re
import spacy
from stock_cap_processor import filter_stocks
import pandas as pd
import time
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions.txt"

def extract_dates(comment):
    timer = time.time()
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(comment)
    date = [ent for ent in doc.ents if ent.label_ == "DATE"]
    endtimer = time.time()
    print("time for date extractor: ", timer-endtimer)
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
        
def save_to_excel(comment, stock, price, date, label):
    file = "prepped_stocks.csv"
    df = pd.DataFrame([[comment, stock, price, date, label]], columns=["Comment", "Stock", "Price", "Date", "Label"])
    df.to_csv(file, mode='a', header=not pd.io.common.file_exists(file), index=False)

def grab_junk_comments(data):
    count = 0
    limit = 5000
    with open(file_path, 'r',  encoding="utf-8") as f:
        for line in f:
            if count >= limit:
                break
            comment = json.loads(line)
            data.append([comment['title'], "", "", "", 0])
            df = pd.DataFrame(data)
            df.to_csv('prepped_stocks.csv', mode='a', index=False, header=False)
            count += 1
            print(count)

def grab_good_comments(data):
    count = 0
    limit = 2000
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if count >= limit:
                break
            comment = json.loads(line)
            stock = extract_stocks(comment['title'])
            price = extract_prices(comment['title'])
            date = extract_dates(comment['title'])
            if stock is not None and price is not None and date is not None:
                data.append([comment['title'], stock, price, date, 1])
                count += 1
                print(count)
                print(comment['title'], stock, price, date)
        df = pd.DataFrame(data, columns=["Comment", "Stock", "Price", "Date", "Label"])
        df.to_csv(f"prepped_stocks.csv", index=False)

def count_positives():
    with open('prepped_stocks.csv', "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if row["Label"].strip() == "1":
                count += 1
        print(count)

def main():
    data = []
    grab_junk_comments(data)
    
main()
 
                 
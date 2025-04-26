#old heuristic I used to get my initial training data. Not used anymore, just here so you can see what I used for the very first iteration
import csv
import json
from pathlib import Path
import re
import spacy
import pandas as pd
import time
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions.txt"

#basic heuristic for looking for dates using the spacy package, very slow
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

#basic heuristic to look for price patterns 
def extract_prices(comment):
    pattern = r'(?:^|(?<![\d.]))(\$?\d+\.\d{1,2})(?!\.\d)(?=$|[^\d.])'
    match = re.search(pattern, comment)
    if match:
        return match.group()
    else:
        return None

#looked for valid stock tickers based on a list downloaded from stockanalysis.com
def extract_stocks(comment):
    stock_tickers = filter_stocks()
    for stock_ticker in stock_tickers:
        if stock_ticker in comment:
            return stock_ticker

#excel method to store results       
def save_to_excel(comment, stock, price, date, label):
    file = "regression_model_training_data.csv"
    df = pd.DataFrame([[comment, stock, price, date, label]], columns=["Comment", "Stock", "Price", "Date", "Label"])
    df.to_csv(file, mode='a', header=not pd.io.common.file_exists(file), index=False)
    
#this was for grabbing some extra basic junk training data, was later abandoned
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
            df.to_csv('regression_model_training_data.csv', mode='a', index=False, header=False)
            count += 1
            print(count)

#grab more valid training data
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
        df.to_csv(f"regression_model_training_data.csv", index=False)

#count the number of good comments I currently had
def count_positives():
    with open('regression_model_training_data.csv', "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if row["Label"].strip() == "1":
                count += 1
        print(count)

#method to filter the stocks for the information I needed, and append a $ to any stock less than 2 symbols otherwise it'd constantly be matching garbage
def filter_stocks():
    df = pd.read_csv("stock_market/stocks.csv")
    df['Symbol'] = df['Symbol'].astype(str)
    df.loc[df['Symbol'].str.len() <= 2, 'Symbol'] = '$' + df.loc[df['Symbol'].str.len() <= 2, 'Symbol']
    combined = pd.concat([df['Symbol']], ignore_index=True)
    combined = combined.sort_values(key=lambda x: x.str.len(), ascending=False)
    return combined.values
    
def main():
    data = []
    grab_junk_comments(data)
    
main()
 
                 
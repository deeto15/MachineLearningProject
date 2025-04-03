from pathlib import Path
from transformers import AutoTokenizer, AutoModelForTokenClassification, TokenClassificationPipeline
import torch, json, csv, os

model_path = "./ner-output"
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions.txt"
script_dir = Path(__file__).resolve().parent
output_path = script_dir / "ner_results.csv"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForTokenClassification.from_pretrained(model_path)
device = 0 if torch.cuda.is_available() else -1

ner_pipeline = TokenClassificationPipeline(
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
    device=device
)

def read_file_reverse(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return reversed(f.readlines())

def process_file_in_batches_reverse(file_path, batch_size=32):
    lines = read_file_reverse(file_path)
    batch = []
    for line in lines:
        try:
            data = json.loads(line)
            comment = data.get("title", "").strip()
            if not comment:
                continue
            batch.append(comment)
            if len(batch) == batch_size:
                results = ner_pipeline(batch)
                yield batch, results
                batch = []
        except json.JSONDecodeError:
            continue
    if batch:
        results = ner_pipeline(batch)
        yield batch, results

required_entities = {"TICKER", "PRICE", "DATE"}
threshold = 0.60

with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Comment", "Stock", "Price", "Date", "Label", "StockScore", "PriceScore", "DateScore"])
    submission_count = 0
    
    for comments, batch_results in process_file_in_batches_reverse(file_path, batch_size=32):
        for comment, entities in zip(comments, batch_results):
            filtered = [e for e in entities if e['score'] > threshold]
            grouped = {}
            for e in filtered:
                if e['entity_group'] not in grouped:
                    grouped[e['entity_group']] = (e['word'], e['score'])
            if required_entities.issubset(grouped):
                ticker_word, ticker_score = grouped["TICKER"]
                price_word, price_score = grouped["PRICE"]
                date_word, date_score = grouped["DATE"]
                price_word = price_word.replace(" ", "")
                date_word = date_word.replace(" ", "")
                writer.writerow([
                    comment,
                    ticker_word,
                    price_word,
                    date_word,
                    1,
                    f"{ticker_score:.4f}",
                    f"{price_score:.4f}",
                    f"{date_score:.4f}"
                ])
                submission_count += 1
                print(f"Submitted: {submission_count}")

print(f"\nTotal submitted: {submission_count}")


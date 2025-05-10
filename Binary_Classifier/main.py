import csv
import json
import random
from pathlib import Path

import pandas as pd
from BERT_loader import load_model
from predictions import tokens
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

output_csv = Path("regression_model_training_data.csv")
WSBComments = (
    Path.home() / "Downloads" / "wallstreetbets_comments" / "wallstreetbets_comments"
)
file_path = (
    Path.home()
    / "Downloads"
    / "wallstreetbets_submissions"
    / "wallstreetbets_submissions"
)
file_exists = output_csv.exists()


def predict_intent(pipeline, example_dict):
    return pipeline.predict(example_dict["Comment"])


def generate_data():
    pipeline = load_model()
    with (
        open(WSBComments, "r", encoding="utf-8") as f,
        open(output_csv, "a", newline="", encoding="utf-8") as out,
    ):
        writer = csv.writer(out)
        if not file_exists:
            writer.writerow(
                [
                    "Comment",
                    "Stock",
                    "Price",
                    "Date",
                    "Label",
                    "StockScore",
                    "PriceScore",
                    "DateScore",
                ]
            )
        for row in f:
            line = json.loads(row)
            result = tokens(line["title"])
            if result:
                decision, confidence = predict_intent(pipeline, result)
                print(decision, confidence)
                writer.writerow(
                    [
                        result.get("Comment", ""),
                        result.get("Stock", ""),
                        result.get("Price", ""),
                        result.get("Date", ""),
                        decision,
                        result.get("StockScore", ""),
                        result.get("PriceScore", ""),
                        result.get("DateScore", ""),
                    ]
                )


def preview_data_random_sample(sample_size=10000, batch_size=32, file_path=WSBComments):
    pipeline = load_model()
    tokenized = []
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= sample_size:
                break
            item = json.loads(line)
            entry = tokens(item["body"])
            if entry:
                tokenized.append(entry)
    if not tokenized:
        return
    comments = [e["Comment"] for e in tokenized]
    preds, confs = pipeline.predict_batch(comments, batch_size=batch_size)
    for e, p, c in zip(tokenized, preds, confs):
        print(f"\nComment: {e['Comment']}")
        print(f"→ Stock: {e['Stock']} (Score: {e['StockScore']})")
        print(f"→ Price: {e['Price']} (Score: {e['PriceScore']})")
        print(f"→ Date : {e['Date']} (Score: {e['DateScore']})")
        print(f"→ Decision: {p} (Confidence: {c:.4f})")


def evaluate_and_show_misses():
    df = pd.read_csv("NER_Classifier/regression_model_training_data.csv")
    df.drop(
        columns=["Stock", "Price", "Date", "StockScore", "PriceScore", "DateScore"],
        inplace=True,
        errors="ignore",
    )
    X = df[["Comment"]]
    y_true = df["Label"].astype(int)
    pipeline = load_model()
    y_pred = [pipeline.predict(row["Comment"])[0] for _, row in X.iterrows()]
    y_proba = [pipeline.predict(row["Comment"])[1] for _, row in X.iterrows()]
    df["Predicted"] = y_pred
    df["Confidence"] = y_proba
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, digits=4))
    print("Confusion Matrix:")
    print(confusion_matrix(y_true, y_pred))
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
    false_positives = df[(df["Label"] == 0) & (df["Predicted"] == 1)]
    false_negatives = df[(df["Label"] == 1) & (df["Predicted"] == 0)]
    print("\nFalse Positives (junk predicted as good):")
    print(
        false_positives[["Comment", "Confidence"]]
        .sort_values(by="Confidence", ascending=False)
        .head(100)
    )
    print("\nFalse Negatives (good missed as junk):")
    print(
        false_negatives[["Comment", "Confidence"]]
        .sort_values(by="Confidence", ascending=False)
        .head(100)
    )


preview_data_random_sample()

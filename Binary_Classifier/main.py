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
        for i, row in enumerate(f):
            if i < 500_000:
                continue
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


def preview_data_random_sample(sample_size=25000):
    pipeline = load_model()
    selected_rows = []
    with open(WSBComments, "r", encoding="utf-8") as f:
        for idx, row in enumerate(f):
            if idx < sample_size:
                selected_rows.append(row)
            else:
                r = random.randint(0, idx)
                if r < sample_size:
                    selected_rows[r] = row
    for row in selected_rows:
        line = json.loads(row)
        result = tokens(line["body"])
        if result:
            decision, confidence = predict_intent(pipeline, result)
            print(f"\nComment: {result.get('Comment', '')}")
            print(
                f"→ Stock: {result.get('Stock', '')} (Score: {result.get('StockScore', '')})"
            )
            print(
                f"→ Price: {result.get('Price', '')} (Score: {result.get('PriceScore', '')})"
            )
            print(
                f"→ Date : {result.get('Date', '')} (Score: {result.get('DateScore', '')})"
            )
            print(f"Prediction: {decision} (Model Confidence: {confidence:.4f})")


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


preview_data_random_sample(sample_size=25000)

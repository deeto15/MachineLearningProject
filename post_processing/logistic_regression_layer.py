import csv
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from post_processing.training_data import tokens
import json
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def load_model():
    df = pd.read_csv("post_processing/regression_model_training_data.csv")
    df.drop(columns=['Stock', 'Price', 'Date', 'StockScore', 'PriceScore', 'DateScore'], inplace=True, errors='ignore')
    X = df[['Comment']]
    y = df['Label']

    text_vectorizer = TfidfVectorizer(max_features=300)
    preprocessor = ColumnTransformer(transformers=[
        ('text', text_vectorizer, 'Comment')
    ])

    pipeline = Pipeline(steps=[
        ('features', preprocessor),
        ('clf', LogisticRegression(max_iter=1000, class_weight='balanced'))
    ])

    pipeline.fit(X, y)

    return pipeline

def predict_intent(pipeline, example_dict):
    example = pd.DataFrame([example_dict])
    proba = pipeline.predict_proba(example)[0]
    prediction = int(proba[1] >= 0.5)  # binary classification: 1 = keep, 0 = discard
    confidence = proba[1] if prediction == 1 else proba[0]
    return prediction, confidence

pipeline = load_model()
output_file = Path("post_processing") / "regression_model_training_data.csv"
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions" / "wallstreetbets_submissions"
file_exists = output_file.exists()

with open(file_path, 'r', encoding='utf-8') as f, open(output_file, 'a', newline='', encoding='utf-8') as out:
    writer = csv.writer(out)
    if not file_exists:
        writer.writerow(['Comment', 'Stock', 'Price', 'Date', 'Label', 'StockScore', 'PriceScore', 'DateScore'])

    for i, row in enumerate(f):
        if i < 500_000:
            continue

        line = json.loads(row)
        result = tokens(line['title'])
        if result:
            decision, confidence = predict_intent(pipeline, result)
            print(decision, confidence)
            writer.writerow([
                result.get('Comment', ''),
                result.get('Stock', ''),
                result.get('Price', ''),
                result.get('Date', ''),
                decision,
                result.get('StockScore', ''),
                result.get('PriceScore', ''),
                result.get('DateScore', ''),
            ])
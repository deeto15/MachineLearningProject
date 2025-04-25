import csv
import pandas as pd
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from predictions import tokens

output_csv = Path("regression_model_training_data.csv")
WSBComments = Path.home() / "Downloads" / "wallstreetbets_comments" / "wallstreetbets_comments"
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions" / "wallstreetbets_submissions"
file_exists = output_csv.exists()

# Custom transformer that wraps the sentence transformer
class SentenceEmbeddingTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return self.model.encode(X['Comment'].tolist(), convert_to_numpy=True)

# Defines a logistic regression pipeline using sentence embeddings
def load_model():
    df = pd.read_csv("post_processing/regression_model_training_data.csv")
    df.drop(columns=['Stock', 'Price', 'Date', 'StockScore', 'PriceScore', 'DateScore'], inplace=True, errors='ignore')
    X = df[['Comment']]
    y = df['Label'].astype(int)

    pipeline = Pipeline(steps=[
        ('embed', SentenceEmbeddingTransformer()),
        ('clf', LogisticRegression(max_iter=1000, class_weight='balanced'))
    ])
    pipeline.fit(X, y)
    return pipeline

#predict the confidence of the prediction
def predict_intent(pipeline, example_dict):
    example = pd.DataFrame([example_dict])
    proba = pipeline.predict_proba(example)[0]
    prediction = int(proba[1] >= 0.5)
    confidence = proba[1] if prediction == 1 else proba[0]
    return prediction, confidence

#use this if you want more training data in the dataset
def generate_data():
    pipeline = load_model()
    with open(file_path, 'r', encoding='utf-8') as f, open(output_csv, 'a', newline='', encoding='utf-8') as out:
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

#use this if you just wanna see it work
def preview_data():
    pipeline = load_model()
    with open(WSBComments, 'r', encoding='utf-8') as f:
        for row in f:
            line = json.loads(row)
            result = tokens(line['body'])
            if result:
                decision, confidence = predict_intent(pipeline, result)
                print(f"\nComment: {result.get('Comment', '')}")
                print(f"→ Stock: {result.get('Stock', '')} (Score: {result.get('StockScore', '')})")
                print(f"→ Price: {result.get('Price', '')} (Score: {result.get('PriceScore', '')})")
                print(f"→ Date : {result.get('Date', '')} (Score: {result.get('DateScore', '')})")
                print(f"Prediction: {decision} (Model Confidence: {confidence:.4f})")

#shows you how well the regression model works on its training data and what it misses so you can inspect for patterns it misses
def evaluate_and_show_misses():
    df = pd.read_csv("post_processing/regression_model_training_data.csv")
    df.drop(columns=['Stock', 'Price', 'Date', 'StockScore', 'PriceScore', 'DateScore'], inplace=True, errors='ignore')
    X = df[['Comment']]
    y_true = df['Label'].astype(int)
    pipeline = load_model()
    y_pred = pipeline.predict(X)
    y_proba = pipeline.predict_proba(X)[:, 1]
    df['Predicted'] = y_pred
    df['Confidence'] = y_proba
    
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, digits=4))
    print("Confusion Matrix:")
    print(confusion_matrix(y_true, y_pred))
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
    
    false_positives = df[(df['Label'] == 0) & (df['Predicted'] == 1)]
    false_negatives = df[(df['Label'] == 1) & (df['Predicted'] == 0)]
    
    print("\nFalse Positives (junk predicted as good):")
    print(false_positives[['Comment', 'Confidence']].sort_values(by='Confidence', ascending=False).head(100))
    false_positives[['Comment']].to_csv("false_positives.csv", index=False)

    print("\nFalse Negatives (good missed as junk):")
    print(false_negatives[['Comment', 'Confidence']].sort_values(by='Confidence', ascending=False).head(100))
    false_negatives[['Comment']].to_csv("false_negatives.csv", index=False)

preview_data()

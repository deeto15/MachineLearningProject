from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import pandas as pd
stocks = pd.read_csv("prepped_stocks.csv")

def process_labels():
    positiveLabel = pd.read_csv("pre_processing/prepped_stocks.csv")
    negativeLabel = pd.read_csv("pre_processing/unprepped_stocks.csv")
    positiveLabel['Label'] = 1
    negativeLabel['Label'] = 0
    data = pd.concat([positiveLabel, negativeLabel], ignore_index=True)
    return data

def logits(data):
    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(data["Comment"])
    y = data['Label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    prediction = model.predict(X_test)
    print(classification_report(y_test, prediction))
    print(accuracy_score(y_test, prediction))

logits(stocks)

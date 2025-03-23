from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import pandas as pd
from sklearn.pipeline import Pipeline
stocks = pd.read_csv("pre_processing/prepped_stocks.csv")

def logits(data):
    print(stocks.columns)
    stocks["Price"] = stocks["Price"].str.replace("$", "").str.replace("%", "").astype(float)
    stocks["Date"] = stocks["Date"].str.replace("[", "").str.replace("]", "")
    X = data["Comment"]
    y = data.drop("Comment", axis=1)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train.values.reshape(-1,1), y_train)
    prediction = model.predict(X_test)
    print(classification_report(y_test, prediction))
    print(accuracy_score(y_test, prediction))

logits(stocks)

def bla(data):
    stocks["Comment"] = stocks["Comment"].fillna("")
    stocks["Date"] = stocks["Date"].fillna("")
    stocks["Stock"] = stocks["Stock"].fillna("")
    stocks["Price"] = stocks["Price"].fillna("0")
    preprocessor = ColumnTransformer([
        ("comment", TfidfVectorizer(), "Comment"),
        ("date", TfidfVectorizer(), "Date"),
        ("stock", TfidfVectorizer(), "Stock"),
        ("num", StandardScaler(), "Price"),
    ])
    
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000))
    ])
    X = data.drop("Label", axis=1)
    y = data['Label']
    
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Load and sanitize data
df = pd.read_csv("regression_model_training_data.csv")
df.drop(columns=['Stock', 'Price', 'Date'], inplace=True, errors='ignore')


# Force numeric types for scores BEFORE split
for col in ['StockScore', 'PriceScore', 'DateScore']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Split
X = df[['Comment', 'StockScore', 'PriceScore', 'DateScore']]
y = df['Label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# TF-IDF + score passthrough
text_vectorizer = TfidfVectorizer(max_features=300)
preprocessor = ColumnTransformer(transformers=[
    ('text', text_vectorizer, 'Comment'),
    ('scores', 'passthrough', ['StockScore', 'PriceScore', 'DateScore'])
])

# Pipeline
pipeline = Pipeline(steps=[
    ('features', preprocessor),
    ('clf', LogisticRegression(max_iter=1000, class_weight='balanced'))
])

# Train
pipeline.fit(X_train, y_train)

# Evaluate
y_pred = pipeline.predict(X_test)
print(classification_report(y_test, y_pred))
# Inference — make sure columns match training set
example = pd.DataFrame([{
    'Comment': "Oil hits new $70 low. 9mo ago, JPM called for $185 by Dec. They’re all clowns",
    'StockScore': 0.8651,
    'PriceScore': 0.7625,
    'DateScore': 0.6359
}])

prediction = pipeline.predict(example)[0]
print("Valid trade intent" if prediction == 1 else "Discard")

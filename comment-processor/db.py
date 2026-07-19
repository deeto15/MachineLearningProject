# SQLite store for processed comments, written to a volume so it survives restarts
import os
import sqlite3

DB_PATH = os.getenv("COMMENTS_DB_PATH", "/data/comments.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    body TEXT,
    author_id TEXT,
    author_name TEXT,
    is_post INTEGER,
    source TEXT,
    created_unix INTEGER,
    stock TEXT,
    stock_score REAL,
    price TEXT,
    price_score REAL,
    date TEXT,
    date_score REAL,
    formatted_date TEXT,
    option_type TEXT,
    option_type_score REAL,
    prediction INTEGER,
    confidence REAL,
    ner_model TEXT,
    binary_model TEXT,
    processed_at TEXT DEFAULT (datetime('now'))
)
"""

INSERT = """
INSERT OR REPLACE INTO comments (
    id, body, author_id, author_name, is_post, source, created_unix,
    stock, stock_score, price, price_score, date, date_score, formatted_date,
    option_type, option_type_score, prediction, confidence, ner_model, binary_model
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def save_comments(conn, comments):
    rows = [
        (
            comment.get("id"),
            comment.get("body"),
            comment.get("author_id"),
            comment.get("author_name"),
            1 if comment.get("is_post") else 0,
            comment.get("source"),
            comment.get("created_unix"),
            comment.get("Stock"),
            comment.get("StockScore"),
            comment.get("Price"),
            comment.get("PriceScore"),
            comment.get("Date"),
            comment.get("DateScore"),
            comment.get("FormattedDate"),
            comment.get("OptionType"),
            comment.get("OptionTypeScore"),
            comment.get("Prediction"),
            comment.get("Confidence"),
            comment.get("NERModel"),
            comment.get("BinaryModel"),
        )
        for comment in comments
    ]
    conn.executemany(INSERT, rows)
    conn.commit()

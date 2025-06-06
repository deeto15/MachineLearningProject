CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    body TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_name text NOT NULL,
    is_post BOOLEAN NOT NULL,
    source TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NUlL,
    parent_id TEXT,
    post_id TEXT
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    comment_id TEXT NOT NULL,

    stock TEXT,
    price NUMERIC(12, 2),
    prediction SMALLINT CHECK (prediction in (0, 1)),
    date TEXT,
    formatted_date TEXT,

    stock_score DOUBLE PRECISION,
    price_score DOUBLE PRECISION,
    date_score DOUBLE PRECISION,
    ner_version TEXT,
    binary_model TEXT,
    confidence DOUBLE PRECISION,

    option_type TEXT,
    quantity TEXT,
    premium NUMERIC(12, 2),

    CONSTRAINT fk_comment
        FOREIGN KEY(comment_id)
        REFERENCES comments(id)
);
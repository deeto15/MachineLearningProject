from datetime import datetime, timezone

# queries
insert_comment_query = """
INSERT INTO comments (id, body, author_id, author_name, is_post, source,
                        created_utc, parent_id, post_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;
"""
def insert_comment(cursor, comment):
    # Convert Unix timestamp integer to datetime with timezone UTC
    created_utc = comment.get("created_unix")
    if isinstance(created_utc, int) or isinstance(created_utc, float):
        created_utc_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    else:
        created_utc_dt = None  # or handle missing/invalid timestamp as needed

    cursor.execute(
        insert_comment_query,
        (
            comment.get("id"),
            comment.get("body"),
            comment.get("author_id"),
            comment.get("author_name"),
            comment.get("is_post"),
            comment.get("source"),
            created_utc_dt,
            comment.get("parent_id"),
            comment.get("post_id"),
        )
    )

insert_prediction_query = """
INSERT INTO predictions (
    comment_id, stock, price, date, formatted_date,
    stock_score, price_score, date_score,
    ner_version, binary_model,
    prediction, confidence, option_type, quantity, premium
) VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s,
    %s, %s, %s, %s, %s
)
"""
def insert_prediction(cursor, prediction):
    cursor.execute(insert_prediction_query, (
        prediction['comment_id'],
        prediction.get('stock'),
        prediction.get('price'),
        prediction.get('date'),
        prediction.get('formatted_date'),
        prediction.get('stock_score'),
        prediction.get('price_score'),
        prediction.get('date_score'),
        prediction.get('ner_version'),
        prediction.get('binary_model'),
        prediction.get('prediction'),
        prediction.get('confidence'),
        prediction.get('option_type'),
        prediction.get('quantity'),
        prediction.get('premium')
    ))
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import psycopg
import json

@dataclass
class Comment:
    id: str
    body: str
    author_id: str
    author_name: str
    is_post: bool
    source: str
    created_utc: datetime
    parent_id: str
    post_id: str

    @staticmethod
    def from_json_str(json_str: str):
        data = json.loads(json_str)
        return Comment(
            id=data["id"],
            body=data["body"],
            author_id=data["author_id"],
            author_name=data["author_name"],
            is_post=data["is_post"],
            created_utc=datetime.fromtimestamp(data["created_unix"], tz=timezone.utc),
            parent_id=data["parent_id"],
            post_id=data["post_id"],
            source=data["source"]
        )

    def to_model_input(self) -> dict:
        return [
            {
                'body': self.body,
                'created_unix': self.created_utc.timestamp()
            }
        ]

@dataclass
class CommentPrediction:
    comment_id: str

    stock: str
    price: float
    date: str
    formatted_date: str

    stock_score: float
    price_score: float
    date_score: float
    
    ner_version: str
    binary_model: str
    prediction: int
    confidence: float

    option_type: str = None
    quantity: str = None
    premium: float = None

    def to_json_str(self) -> str:
        data = asdict(self)
        return json.dumps(data)

    @classmethod
    def from_model_output(cls, comment_id: str, model_output: list):
        return cls(
            comment_id=comment_id,
            stock=model_output[0].get("Stock"),
            price=model_output[0].get("Price"),
            date=model_output[0].get("Date"),
            formatted_date=model_output[0].get("Formatted Date"),
            stock_score=model_output[0].get("StockScore"),
            price_score=model_output[0].get("PriceScore"),
            date_score=model_output[0].get("DateScore"),
            ner_version=model_output[0].get("NER Version"),
            binary_model=model_output[0].get("Binary_Model"),
            prediction=model_output[0].get("Prediction"),
            confidence=model_output[0].get("Confidence"),
        )

class CommentsProvider:
    def __init__(self, host, port, db_name, user, password):
        self.conn = psycopg.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port
        )

    # queries
    insert_comment_query = """
    INSERT INTO comments (id, body, author_id, author_name, is_post, source,
                            created_utc, parent_id, post_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;
    """

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

    def insert_comment(self, comment: Comment):
        with self.conn.cursor() as cur:
            cur.execute(
                self.insert_comment_query, (
                    comment.id,
                    comment.body,
                    comment.author_id,
                    comment.author_name,
                    comment.is_post,
                    comment.source,
                    comment.created_utc,
                    comment.parent_id,
                    comment.post_id
                )
            )

        self.conn.commit()

    def insert_prediction(self, prediction: CommentPrediction):
        with self.conn.cursor() as cur:
            cur.execute(self.insert_prediction_query, (
                prediction.comment_id,
                prediction.stock,
                prediction.price,
                prediction.date,
                prediction.formatted_date,
                prediction.stock_score,
                prediction.price_score,
                prediction.date_score,
                prediction.ner_version,
                prediction.binary_model,
                prediction.prediction,
                prediction.confidence,
                prediction.option_type,
                prediction.quantity,
                prediction.premium
            ))

        self.conn.commit()
import json
import logging
import os
import time

import pika

import db
from classifier.ner import predict_comments

BATCH_SIZE = 32
FLUSH_SECONDS = 30
QUEUE_NAME = "comments_raw"


def connect(host, user, password, attempts=12, delay=5):
    credentials = pika.PlainCredentials(username=user, password=password)
    params = pika.ConnectionParameters(host=host, port=5672, credentials=credentials)
    for attempt in range(1, attempts + 1):
        try:
            return pika.BlockingConnection(params)
        except pika.exceptions.AMQPConnectionError:
            logging.info("RabbitMQ not ready (attempt %d/%d), retrying in %ds", attempt, attempts, delay)
            time.sleep(delay)
    raise RuntimeError("Could not connect to RabbitMQ")


def process_batch(batch, db_conn):
    results = predict_comments(batch)
    db.save_comments(db_conn, results)
    for result in results:
        logging.info("Processed comment: %s", result)


def main():
    logging.basicConfig(level=logging.INFO)
    connection = connect(
        os.getenv("RABBITMQ_HOST", "rabbitmq"),
        os.getenv("RABBITMQ_DEFAULT_USER"),
        os.getenv("RABBITMQ_DEFAULT_PASS"),
    )
    channel = connection.channel()
    channel.queue_declare(QUEUE_NAME, durable=True)
    db_conn = db.connect()

    logging.info("Listening for new messages, storing comments in %s", db.DB_PATH)
    batch = []
    # inactivity_timeout lets us flush a partial batch when the queue goes quiet
    for method, _properties, body in channel.consume(QUEUE_NAME, inactivity_timeout=FLUSH_SECONDS):
        if method is None:
            if batch:
                process_batch(batch, db_conn)
                batch.clear()
            continue

        comment = json.loads(body.decode())
        logging.info("Received new comment: %s", comment["body"])
        batch.append(comment)
        channel.basic_ack(method.delivery_tag)

        if len(batch) >= BATCH_SIZE:
            process_batch(batch, db_conn)
            batch.clear()


if __name__ == "__main__":
    main()

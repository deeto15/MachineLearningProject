import os
from time import sleep
import json
import logging

import psycopg
import pika
from Binary_Classifier.predictions import predict_comments
from db import insert_comment, insert_prediction

conn = None
def process_message(ch, method, properties, body):
    messageJSON = json.loads(body.decode())
    result = predict_comments([messageJSON])
    try:
        with conn.cursor() as cursor:
            insert_comment(cursor, messageJSON)
            if len(result) > 0:
                prediction = {
                    "comment_id": messageJSON['id'],  # assuming the comment has an "id"
                    "stock": result[0].get("Stock"),
                    "price": result[0].get("Price"),
                    "date": result[0].get("Date"),
                    "formatted_date": result[0].get("Formatted Date"),
                    "stock_score": result[0].get("StockScore"),
                    "price_score": result[0].get("PriceScore"),
                    "date_score": result[0].get("DateScore"),
                    "ner_version": result[0].get("NER Version"),
                    "binary_model": result[0].get("Binary_Model"),
                    "prediction": result[0].get("Prediction"),
                    "confidence": result[0].get("Confidence")
                }

                insert_prediction(cursor, prediction) 
            conn.commit()
        logging.info(f"Inserted comment {messageJSON}")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(e) 
        conn.rollback()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # wait for rabbitmq to start and scraper to setup queue
    sleep(7)
    logging.info("Attempting Postgres connection")
    conn = psycopg.connect(
        dbname=os.getenv("POSTGRES_DB_NAME"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
    )

    logging.info("Starting")
    rabbit_user = os.getenv("RABBITMQ_DEFAULT_USER")
    rabbit_password = os.getenv("RABBITMQ_DEFAULT_PASS")
    credentials = pika.PlainCredentials(username=rabbit_user, password=rabbit_password)
    rabbit_host = os.getenv("RABBITMQ_HOST")

    connection_params = pika.ConnectionParameters(
        host=rabbit_host,
        port=5672,
        virtual_host='/',
        credentials=credentials
    )

    logging.info("Attempting RabbitMQ Connection")
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    channel.queue_declare("comments_raw", True, True, False, False)
    channel.basic_consume("comments_raw", process_message, auto_ack=False) 

    channel.basic_qos(prefetch_count=1)

    logging.info("Listening for new messages")
    channel.start_consuming()

import os
from time import sleep
import json
import logging

import pika

from Binary_Classifier.predictions import predict_comments

BATCH_SIZE=32
batch = []

last_tag = None

def process_message(ch, method, properties, body):
    global last_tag

    messageJSON = json.loads(body.decode())
    batch.append(messageJSON)
    last_tag = method.delivery_tag

    # process the batch when it reaches its limit and reset it
    if len(batch) == BATCH_SIZE:
        results = predict_comments(batch)
        logging.info(f"Got {len(results)} good comments from batch")

        for result in results:
            logging.info(f"Good comment: {result}")
        
        ch.basic_ack(delivery_tag=last_tag, multiple=True)
        batch.clear() 

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # wait for rabbitmq to start and scraper to setup queue
    sleep(7)
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

    logging.info("Listening for new messages")
    channel.start_consuming()

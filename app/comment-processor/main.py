import os
from time import sleep
import logging

from Binary_Classifier.predictions import predict_comments

from comments import CommentsProvider, Comment, CommentPrediction
from rabbit import RabbitClient

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # wait for rabbitmq to start and scraper to setup queue
    sleep(7)
    dbname=os.getenv("POSTGRES_DB_NAME")
    user=os.getenv("POSTGRES_USER")
    password=os.getenv("POSTGRES_PASSWORD")
    host=os.getenv("POSTGRES_HOST")
    port=os.getenv("POSTGRES_PORT")

    # set up comments provider
    comments_provider = CommentsProvider(host, port, dbname, user, password)

    rabbit_user = os.getenv("RABBITMQ_DEFAULT_USER")
    rabbit_password = os.getenv("RABBITMQ_DEFAULT_PASS")
    rabbit_host = os.getenv("RABBITMQ_HOST")

    # set up rabbit client
    rabbit_client = RabbitClient(rabbit_host, rabbit_user, rabbit_password)

    # handles processing, insertion, and redirection of comment predictions to queue
    def process_comment(comment: Comment):
        print(f"Received comment: {comment.body}")
        comments_provider.insert_comment(comment)

        model_output = predict_comments(comment.to_model_input())
        if len(model_output) == 0:
            return

        prediction = CommentPrediction.from_model_output(comment.id, model_output)

        comments_provider.insert_prediction(prediction)
        rabbit_client.publish("comments_processed", prediction)
    
    # start consuming and block
    rabbit_client.start_consuming("comments_raw", process_comment, Comment)

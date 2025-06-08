import pika
import traceback
import json

class RabbitClient:
    def consume_message(self, ch, method, properties, body):
        message = self.data_class.from_json(body.decode())

        try:
            self.controller(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(e)

    def __init__(self, host: str, username: str, password: str):
        credentials = pika.PlainCredentials(username=username, password=password)
        conn_params = pika.ConnectionParameters(
            host=host,
            port=5672,
            virtual_host='/',
            credentials=credentials
        )

        self.connection = pika.BlockingConnection(conn_params)
        self.channel = self.connection.channel()

    def start_consuming(self, queue_name: str, controller, data_class):
        def callback(ch, method, properties, body):
            message = data_class.from_json_str(body.decode())
            try:
                controller(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                traceback.print_exc()

        self.channel.queue_declare(queue_name, False, True, False, False)
        self.channel.basic_consume(queue_name, callback, auto_ack=False)
        self.channel.start_consuming()

    def publish(self, queue_name: str, message):
        self.channel.queue_declare(queue_name, False, True, False, False)

        if hasattr(message, "to_json_str"):
            body = message.to_json_str()
        else:
            body = json.dumps(message)
        
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2)
        )




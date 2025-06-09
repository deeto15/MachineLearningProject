package rabbit

import (
	"encoding/json"
	"fmt"
	"log"

	"github.com/rabbitmq/amqp091-go"
)

type RabbitMQClient struct {
	rabbitChannel *amqp091.Channel
}

func NewRabbitMQClient(username string, password string, addr string) *RabbitMQClient {
	formatted := fmt.Sprintf("amqp://%s:%s@%s/", username, password, addr)
	conn, err := amqp091.Dial(formatted)
	if err != nil {
		log.Fatal("Error connecting to Rabbit: ", err, formatted)
	}

	rabbitChannel, err := conn.Channel()
	if err != nil {
		log.Fatal(err)
	}

	return &RabbitMQClient{rabbitChannel}
}

func StartConsuming[T any](r *RabbitMQClient, queueName string, dest chan<- *T) {
	q, err := r.rabbitChannel.QueueDeclare(
		queueName,
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatal(err)
	}

	msgs, err := r.rabbitChannel.Consume(
		q.Name,
		"",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatal(err)
	}

	for msg := range msgs {
		var data T
		if err := json.Unmarshal(msg.Body, &data); err != nil {
			log.Println("Unmarshaling error: ", err)
		}
		dest <- &data
	}
}

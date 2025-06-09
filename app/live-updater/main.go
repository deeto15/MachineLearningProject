package main

import (
	"live-updater/rabbit"
	"live-updater/types"
	"log"
	"os"
	"time"
)

func main() {
	// wait for rabbit
	time.Sleep(7 * time.Second)

	rabbitUsername := os.Getenv("RABBITMQ_USER")
	rabbitPassword := os.Getenv("RABBITMQ_PASSWORD")
	rabbitHost := os.Getenv("RABBITMQ_ADDR")

	client := rabbit.NewRabbitMQClient(rabbitUsername, rabbitPassword, rabbitHost)

	predictions := make(chan *types.Prediction, 10)
	go rabbit.StartConsuming(client, "comments_processed", predictions)

	for pred := range predictions {
		log.Println(pred)
	}
}

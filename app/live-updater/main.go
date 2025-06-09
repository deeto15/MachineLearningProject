package main

import (
	"live-updater/auth"
	"live-updater/ws"
	"log"
	"net/http"
	"os"
	"time"
)

func main() {

	/*
		rabbitUsername := os.Getenv("RABBITMQ_USER")
		rabbitPassword := os.Getenv("RABBITMQ_PASSWORD")
		rabbitHost := os.Getenv("RABBITMQ_ADDR")

		client := rabbit.NewRabbitMQClient(rabbitUsername, rabbitPassword, rabbitHost)

		predictions := make(chan *types.Prediction, 10)
		go rabbit.StartConsuming(client, "comments_processed", predictions)
	*/

	secret := os.Getenv("JWT_SECRET")
	http.HandleFunc("/ws", auth.AuthMiddleware(secret, ws.Handler))

	// for testing
	token, err := auth.GenerateJWT(secret, "123123123123", []string{"predictions"}, 24*time.Hour)
	if err != nil {
		log.Fatal(err)
	}
	log.Println(token)

	log.Println("Server started on port :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}

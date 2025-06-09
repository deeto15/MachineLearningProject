package ws

import (
	"encoding/json"
	"live-updater/auth"
	"log"
	"net/http"

	"github.com/gorilla/websocket"
)

type WSClientMessage struct {
	Action string `json:"action"`
	Topic  string `json:"topic"`
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin:     func(r *http.Request) bool { return true },
}

func Handler(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r)
	if claims == nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)

	if err != nil {
		log.Println("Upgrade err: ", err)
		return
	}

	defer conn.Close()

	for {
		_, messageBytes, err := conn.ReadMessage()
		if err != nil {
			log.Println("Read error: ", err)
			break
		}

		var message WSClientMessage
		err = json.Unmarshal(messageBytes, &message)
		if err != nil {
			log.Println("JSON unmarshal error on client message:", err)
			break
		}

		switch message.Action {
		case "subscribe":
			if !claims.HasTopic(message.Topic) {
				WriteError(conn, UnauthorizedTopicError)
				continue
			}

		case "unsubscribe":
			if !claims.HasTopic(message.Topic) {
				WriteError(conn, UnauthorizedTopicError)
				continue
			}
		}

	}
}

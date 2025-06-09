package ws

import (
	"encoding/json"

	"github.com/gorilla/websocket"
)

type WSError struct {
	Error string `json:"error"`
}

var UnauthorizedTopicError = WSError{"unauthorized topic"}

func WriteError(conn *websocket.Conn, error WSError) {
	bytes, _ := json.Marshal(error)
	conn.WriteMessage(websocket.TextMessage, bytes)
}

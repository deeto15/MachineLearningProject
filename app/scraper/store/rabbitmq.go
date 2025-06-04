package store

import (
	"encoding/json"
	"fmt"
	"log"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/vartanbeno/go-reddit/v2/reddit"
)

type RabbitMQStore struct {
	postChan      chan *reddit.Post
	commentChan   chan *reddit.Comment
	rabbitChannel *amqp.Channel
	rabbitQueue   *amqp.Queue
}

// setup a rabbit connection, channel, and queue
func NewRabbitMQStore(username string, password string, addr string, queueName string) *RabbitMQStore {
	formatted := fmt.Sprintf("amqp://%s:%s@%s/", username, password, addr)
	conn, err := amqp.Dial(formatted)

	if err != nil {
		log.Fatal("Error connecting to Rabbit: ", err, formatted)
	}

	rabbitChannel, err := conn.Channel()
	if err != nil {
		log.Fatal(err)
	}

	q, err := rabbitChannel.QueueDeclare(
		"comments_raw",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatal(err)
	}

	postChan := make(chan *reddit.Post, 10)
	commentChan := make(chan *reddit.Comment, 10)

	return &RabbitMQStore{
		postChan,
		commentChan,
		rabbitChannel,
		&q,
	}
}

// combines common post and comment fields since we want to treat them as the same
type SendableComment struct {
	ID          string `json:"id"`
	Body        string `json:"body"`
	AuthorID    string `json:"author_id"`
	AuthorName  string `json:"author_name"`
	IsPost      bool   `json:"is_post"` // true if post false for comment
	Source      string `json:"source"`  // ex. r/wallstreetbets
	CreatedUnix int64  `json:"created_unix"`
}

// send a sendable comment to the appropriate rabbit channel and queue, could be either a post or comment
func sendComment(rabbitChannel *amqp.Channel, rabbitQueue *amqp.Queue, comment *SendableComment) {
	postBytes, err := json.Marshal(comment)
	if err != nil {
		log.Printf("Error converting %s to JSON\n", comment.ID)
	}

	err = rabbitChannel.Publish(
		"",
		rabbitQueue.Name,
		false,
		false,
		amqp.Publishing{
			ContentType:  "application/json",
			Body:         postBytes,
			DeliveryMode: amqp.Persistent,
		},
	)

	if err != nil {
		log.Printf("Error sending %s to Rabbit\n", comment.ID)
		return
	}
}

// listen for new incoming comments/posts and send them to Rabbit
// merges posts/comments into the same
func (r *RabbitMQStore) Start() {
	for {
		select {
		case newPost := <-r.postChan:
			msg := &SendableComment{
				newPost.ID,
				newPost.Title + " " + newPost.Body,
				newPost.AuthorID,
				newPost.Author,
				true,
				newPost.SubredditNamePrefixed,
				newPost.Created.Unix(),
			}

			sendComment(r.rabbitChannel, r.rabbitQueue, msg)

		case newComment := <-r.commentChan:
			msg := &SendableComment{
				newComment.ID,
				newComment.Body,
				newComment.AuthorID,
				newComment.Author,
				false,
				newComment.SubredditNamePrefixed,
				newComment.Created.Unix(),
			}

			sendComment(r.rabbitChannel, r.rabbitQueue, msg)
		}
	}
}

// receiving new comments and posts from redis through these channels
func (r RabbitMQStore) CommentChannel() chan<- *reddit.Comment {
	return r.commentChan
}

func (r RabbitMQStore) PostChannel() chan<- *reddit.Post {
	return r.postChan
}

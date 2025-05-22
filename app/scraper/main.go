package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/joho/godotenv"
	"github.com/vartanbeno/go-reddit/v2/reddit"
)

func main() {
	godotenv.Load()
	id := os.Getenv("REDDIT_CLIENT_ID")
	secret := os.Getenv("REDDIT_CLIENT_SECRET")
	username := os.Getenv("REDDIT_USERNAME")
	password := os.Getenv("REDDIT_PASSWORD")

	credentials := reddit.Credentials{ID: id, Secret: secret, Username: username, Password: password}
	client, err := reddit.NewClient(credentials)
	if err != nil {
		log.Fatal(err)
	}

	postOpts := reddit.ListOptions{
		Limit: 5,
	}
	posts, _, err := client.Subreddit.NewPosts(context.Background(), "wallstreetbets", &postOpts)

	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Got %d posts successfully\n", len(posts))

	for _, post := range posts {
		fmt.Println(post.Title)
	}

}

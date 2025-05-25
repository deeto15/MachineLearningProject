package main

import (
	"log"
	"os"
	"scraper/monitor"
	"time"

	"github.com/go-redis/redis"
	"github.com/joho/godotenv"
	"github.com/vartanbeno/go-reddit/v2/reddit"
)

func main() {
	godotenv.Load()
	id := os.Getenv("REDDIT_CLIENT_ID")
	secret := os.Getenv("REDDIT_CLIENT_SECRET")
	username := os.Getenv("REDDIT_USERNAME")
	password := os.Getenv("REDDIT_PASSWORD")

	redisAddr := os.Getenv("REDIS_ADDR")
	rdb := redis.NewClient(&redis.Options{
		Addr:     redisAddr,
		Password: "",
		DB:       0,
	})
	pong, err := rdb.Ping().Result()
	if err != nil {
		log.Fatal(err)
	}
	log.Println(pong)

	credentials := reddit.Credentials{ID: id, Secret: secret, Username: username, Password: password}
	client, err := reddit.NewClient(credentials)

	if err != nil {
		log.Fatal(err)
	}

	// 2 weeks
	postLifetime := 14 * 24 * time.Hour

	subreddit := os.Getenv("SUBREDDIT")

	// check for new comments on every post every 30 seconds
	go monitor.MonitorNewComments(
		subreddit,
		30*time.Second,
		time.Duration(postLifetime),
		rdb,
		client,
	)

	// check for new posts that come in 3 at a time every 30 seconds
	go monitor.MonitorNewPosts(
		subreddit,
		3,
		30*time.Second,
		rdb,
		client,
	)
	select {}

}

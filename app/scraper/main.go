package main

import (
	"log"
	"os"
	"scraper/monitor"
	"strconv"
	"time"

	"github.com/go-redis/redis"
	"github.com/joho/godotenv"
	"github.com/vartanbeno/go-reddit/v2/reddit"
)

func main() {
	// load env variables
	godotenv.Load()
	id := os.Getenv("REDDIT_CLIENT_ID")
	secret := os.Getenv("REDDIT_CLIENT_SECRET")
	username := os.Getenv("REDDIT_USERNAME")
	password := os.Getenv("REDDIT_PASSWORD")
	subreddit := os.Getenv("SUBREDDIT")

	// connect and setup redis
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

	// setup redit client
	credentials := reddit.Credentials{ID: id, Secret: secret, Username: username, Password: password}
	client, err := reddit.NewClient(credentials)
	if err != nil {
		log.Fatal(err)
	}

	// load monitoring parameters and setup monitor options
	pollFrequencySeconds, _ := strconv.Atoi(os.Getenv("POLL_FREQUENCY_SECONDS"))
	postCutoffMinutes, _ := strconv.Atoi(os.Getenv("POST_CUTOFF_MINUTES"))
	postDeletionBufferMinutes, _ := strconv.Atoi(os.Getenv("POST_DELETION_BUFFER_MINUTES"))
	postDeletionFrequencySeconds, _ := strconv.Atoi(os.Getenv("POST_DELETION_FREQUENCY_SECONDS"))
	maxPostsPerPoll, _ := strconv.Atoi(os.Getenv("MAX_POSTS_PER_POLL"))

	opts := &monitor.SubredditMonitorOpts{
		PollFrequency:         time.Duration(pollFrequencySeconds) * time.Second,
		PostCutoff:            time.Duration(postCutoffMinutes) * time.Minute,
		PostDeletionBuffer:    time.Duration(postDeletionBufferMinutes) * time.Minute,
		PostDeletionFrequency: time.Duration(postDeletionFrequencySeconds) * time.Second,
		MaxPostsPerPoll:       maxPostsPerPoll,
	}

	// dummy logger here for now, will be a real comment source later
	logger := monitor.NewMonitorLogger()
	go logger.Start()

	// create and start monitor
	subredditMonitor := monitor.NewSubredditMonitor(
		subreddit,
		logger,
		rdb,
		client,
		opts,
	)

	subredditMonitor.Start()
}

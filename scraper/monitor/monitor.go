package monitor

import (
	"context"
	"fmt"
	"log"
	"scraper/store"
	"time"

	"github.com/go-redis/redis"
	"github.com/vartanbeno/go-reddit/v2/reddit"
	"golang.org/x/time/rate"
)

func (s *SubredditMonitor) monitorNewPosts() {
	ticker := time.NewTicker(s.opts.PollFrequency)
	log.Printf("Starting post monitor for r/%s at %s frequency\n", s.subreddit, s.opts.PollFrequency.String())
	opts := &reddit.ListOptions{
		Limit: s.opts.MaxPostsPerPoll,
	}

	for range ticker.C {
		s.limiter.Wait(context.Background())

		posts, _, err := s.redditClient.Subreddit.NewPosts(context.Background(), s.subreddit, opts)
		if err != nil {
			log.Printf("Error fetching posts from r/%s: %v\n", s.subreddit, err.Error())
		}

		for _, post := range posts {
			s.checkAndStorePost(post)
		}
	}
}

func (s *SubredditMonitor) checkAndStorePost(post *reddit.Post) {
	isNew := store.InsertRedisPost(s.subreddit, post, s.rdb)
	if isNew {
		channel := s.commentsSource.PostChannel()
		channel <- post
	}
}

func (s *SubredditMonitor) monitorNewComments() {
	ticker := time.NewTicker(s.opts.PollFrequency)

	log.Printf("Starting comment monitor for r/%s at %s frequency\n", s.subreddit, s.opts.PollFrequency.String())

	for range ticker.C {
		postIds := store.GetRecentRedisPosts(s.subreddit, s.opts.PostCutoff, s.rdb)
		log.Printf("Getting comments for %d new posts from Redis\n", len(postIds))

		for _, id := range postIds {
			s.GetAllComments(id)
		}
	}
}

// deletes the old comments and posts
func (s *SubredditMonitor) deleteOldPostsAndComments() {
	ticker := time.NewTicker(s.opts.PostDeletionFrequency)

	for range ticker.C {
		log.Println("Checking for old posts")
		postsKey := fmt.Sprintf("seen:%s:posts", s.subreddit)
		commentsKey := fmt.Sprintf("seen:%s:comments", s.subreddit)

		threshold := time.Now().Add(-1*s.opts.PostCutoff + -1*s.opts.PostDeletionBuffer).Unix()
		formatted := fmt.Sprintf("(%d", threshold)
		removedPosts, err := s.rdb.ZRemRangeByScore(postsKey, "-inf", formatted).Result()

		if err != nil {
			log.Printf("Error removing old posts: %v\n", err)
		}

		if removedPosts != 0 {
			log.Printf("Removed %d posts\n", removedPosts)
		}

		removedComments, err := s.rdb.ZRemRangeByScore(commentsKey, "-inf", formatted).Result()
		if err != nil {
			log.Printf("Error removing old comments: %v\n", err)
		}

		if removedComments != 0 {
			log.Printf("Removed %d comments\n", removedComments)
		}
	}
}

// source that receives new monitored posts and comments
type MonitorSource interface {
	CommentChannel() chan<- *reddit.Comment
	PostChannel() chan<- *reddit.Post
}

type SubredditMonitorOpts struct {
	PollFrequency         time.Duration // frequency to poll reddit for new posts
	PostCutoff            time.Duration // lifetime duration to hold onto posts for comment monitoring, posts older than this duration wont be rescraped
	PostDeletionBuffer    time.Duration // buffer to hold onto old posts to make sure newer posts have refilled the backlog
	PostDeletionFrequency time.Duration // frequency to check for and delete old posts
	MaxPostsPerPoll       int           // maximum amount of posts to gather per poll
}

type SubredditMonitor struct {
	subreddit      string
	commentsSource MonitorSource
	rdb            *redis.Client
	redditClient   *reddit.Client
	limiter        *rate.Limiter
	opts           *SubredditMonitorOpts
}

func NewSubredditMonitor(subreddit string, source MonitorSource, rdb *redis.Client, redditClient *reddit.Client, opts *SubredditMonitorOpts) *SubredditMonitor {
	return &SubredditMonitor{
		subreddit,
		source,
		rdb,
		redditClient,
		rate.NewLimiter(1, 1),
		opts,
	}
}

func (s *SubredditMonitor) Start() {
	go s.monitorNewComments()
	go s.monitorNewPosts()
	go s.deleteOldPostsAndComments()
	select {}
}

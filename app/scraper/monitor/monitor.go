package monitor

import (
	"context"
	"log"
	"scraper/store"
	"time"

	"github.com/go-redis/redis"
	"github.com/vartanbeno/go-reddit/v2/reddit"
)

func MonitorNewPosts(subreddit string, maxPostsPerPoll int, pollFrequency time.Duration, rdb *redis.Client, client *reddit.Client) {
	ticker := time.NewTicker(pollFrequency)
	log.Printf("Starting post monitor for r/%s at %s frequency\n", subreddit, pollFrequency.String())
	opts := &reddit.ListOptions{
		Limit: maxPostsPerPoll,
	}

	go func() {
		for range ticker.C {
			posts, _, err := client.Subreddit.NewPosts(context.Background(), subreddit, opts)
			if err != nil {
				log.Printf("Error fetching posts from r/%s: %v\n", subreddit, err.Error())
			}

			for _, post := range posts {
				store.InsertRedisPost(subreddit, post, rdb)
				// track result and eventually pass it to queue
			}
		}
	}()
}

// gets a flattened list of all post's comments instead of the tree structure
func getAllPostComments(postId string, client *reddit.Client) []*reddit.Comment {
	post, _, err := client.Post.Get(context.Background(), postId)
	if err != nil {
		log.Printf("Error fetching comments for postID %s\n", postId)
		return nil
	}

	var result []*reddit.Comment

	var helper func(comments []*reddit.Comment)
	helper = func(comments []*reddit.Comment) {
		for _, c := range comments {
			result = append(result, c)
			if len(c.Replies.Comments) > 0 {
				helper(c.Replies.Comments)
			}
		}
	}

	helper(post.Comments)
	return result
}

func MonitorNewComments(subreddit string, pollFrequency time.Duration, postCutoff time.Duration, rdb *redis.Client, client *reddit.Client) {
	ticker := time.NewTicker(pollFrequency)

	log.Printf("Starting comment monitor for r/%s at %s frequency\n", subreddit, pollFrequency.String())

	go func() {
		for range ticker.C {
			postIds := store.GetRecentRedisPosts(subreddit, postCutoff, rdb)
			log.Printf("Getting comments for %d new posts from Redis\n", len(postIds))

			for _, id := range postIds {
				comments := getAllPostComments(id, client)
				for _, comment := range comments {
					store.InsertRedisComment(subreddit, comment, rdb)
					// do something with new status and put in queue later
				}
			}
		}

	}()
}

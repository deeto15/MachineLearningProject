package store

import (
	"fmt"
	"log"
	"time"

	"github.com/go-redis/redis"
	"github.com/vartanbeno/go-reddit/v2/reddit"
)

// redis operations

// inserts a list of posts to redis sorted set with their Unix timestamp as a score
func InsertRedisPost(subreddit string, post *reddit.Post, rdb *redis.Client) bool {

	key := fmt.Sprintf("seen:%s:posts", subreddit)

	formattedPost := FormatSortedSetEntry(post.Created.Time, post.ID)

	added, err := rdb.ZAdd(key, formattedPost).Result()
	if err != nil {
		log.Println("Error inserting Redis posts")
	}

	if added > 0 {
		log.Printf("Added new post to Redis: %s\n", post.Title)
		return true
	}

	return false
}

// inserts new comments much like posts - could maybe refactor later for DRY
func InsertRedisComment(subreddit string, comment *reddit.Comment, rdb *redis.Client) bool {

	key := fmt.Sprintf("seen:%s:comments", subreddit)

	formattedComment := FormatSortedSetEntry(comment.Created.Time, comment.ID)

	added, err := rdb.ZAdd(key, formattedComment).Result()
	if err != nil {
		log.Println("Error inserting Redis comment")
	}

	if added > 0 {
		log.Printf("Added new comment to Redis: %s\n", comment.Body)

		return true
	}

	return false
}

// gets recent post from redis sorted set, cutOff = age of the posts, ex. younger than 2 weeks
// returns an array of string post IDs
func GetRecentRedisPosts(subreddit string, cutOff time.Duration, rdb *redis.Client) []string {
	limit := time.Now().Add(-cutOff).Unix()
	key := fmt.Sprintf("seen:%s:posts", subreddit)

	zRangeOpts := &redis.ZRangeBy{
		Min: fmt.Sprintf("%d", limit),
		Max: "+inf",
	}
	postIds, err := rdb.ZRangeByScore(key, *zRangeOpts).Result()
	if err != nil {
		log.Println("Error getting recent posts from Redis")
	}

	return postIds
}

// formats a sorted set entry for redis given the score (time) and member
func FormatSortedSetEntry(score time.Time, member string) redis.Z {
	return redis.Z{
		Score:  float64(score.Unix()),
		Member: member,
	}
}

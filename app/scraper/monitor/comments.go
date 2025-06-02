package monitor

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
	"scraper/store"
	"strings"

	"github.com/vartanbeno/go-reddit/v2/reddit"
)

/*

Separate logic for enumerating comments, got quite long

*/

var endpoint = "https://oauth.reddit.com/api/morechildren"

// gets a flattened list of all post's comments instead of the tree structure
func getReplies(surfaceComments []*reddit.Comment) []*reddit.Comment {
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

	helper(surfaceComments)
	return result
}

type Listing struct {
	Things []Thing `json:"things"`
	After  string
}

type Thing struct {
	Kind string      `json:"kind"`
	Data interface{} `json:"data"`
}

type ResponseData struct {
	Data Listing `json:"data"`
}

type ResponseJSON struct {
	JSON ResponseData `json:"json"`
}

// sends a request to the morechildren endpoint, has to be done manually because of no support from go-reddit
func (s *SubredditMonitor) MoreRequest(recentRequest *http.Request, fullID string, childrenIDs []string) {

	// parameters for getting children
	data := url.Values{}
	data.Set("link_id", fullID)
	data.Set("api_type", "json")
	data.Set("sort", "new")
	data.Set("children", strings.Join(childrenIDs, ","))

	// sets headers, gets token by supplying the most recent request sent from the go-reddit client
	req, err := http.NewRequest("POST", endpoint, strings.NewReader(data.Encode()))
	req.Header.Set("Authorization", recentRequest.Header.Get("Authorization"))
	req.Header.Set("User-Agent", s.redditClient.UserAgent())
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")

	if err != nil {
		log.Printf("Error forming request for More on %s: %v\n", fullID, err)
	}

	s.limiter.Wait(context.Background())
	resp, err := s.redditClient.Do(context.Background(), req, nil)
	if err != nil {
		log.Printf("Error sending More request for ID %s: %v\n", fullID, err)
	}

	// read and unmarshal the entire response
	bodyBytes, _ := io.ReadAll(resp.Body)
	var jsonResponse ResponseJSON
	json.Unmarshal(bodyBytes, &jsonResponse)

	// separate More entries and actual Comments
	var mores []*reddit.More
	var comments []*reddit.Comment
	for _, t := range jsonResponse.JSON.Data.Things {
		jsonBytes, _ := json.Marshal(t.Data)

		if t.Kind == "more" {
			var more reddit.More
			json.Unmarshal(jsonBytes, &more)
			mores = append(mores, &more)
		} else if t.Kind == "t1" {
			var comment reddit.Comment
			json.Unmarshal(jsonBytes, &comment)
			comments = append(comments, &comment)
		}
	}

	// batch More Ids and make more recursive calls
	batch := make([]string, 0)
	for _, more := range mores {
		for _, commentID := range more.Children {
			if len(batch) == 100 {
				s.MoreRequest(recentRequest, fullID, batch)
				batch = batch[:0]
			}
			batch = append(batch, commentID)
		}
	}

	// clean up the IDs that got left over (didn't fit into batches of 100)
	if len(batch) > 0 {
		s.MoreRequest(recentRequest, fullID, batch)
	}

	// check for posts that have more to load
	allComments := getReplies(comments)
	for _, comment := range allComments {

		if comment.HasMore() {
			s.MoreRequest(recentRequest, comment.FullID, comment.Replies.More.Children)
		}
	}
}

// recursively uses morechildren reddit api when necessary
func (s *SubredditMonitor) GetAllComments(postID string) {
	log.Printf("Checking post %s for new comments\n", postID)

	s.limiter.Wait(context.Background())
	post, postResp, err := s.redditClient.Post.Get(context.Background(), postID)

	// skip the post for now if there is an error ex. 500 internal error
	if err != nil {
		log.Println("Error getting post: ", err)
		return
	}
	surfaceLevelComments := getReplies(post.Comments)

	for _, comment := range surfaceLevelComments {
		s.checkAndStoreComment(comment)
	}

	// start recursion if the post has more to load
	if post.HasMore() {
		log.Printf("Encountered long post with ID %s needing More request\n", post.Post.ID)
		s.MoreRequest(postResp.Request, post.Post.FullID, post.More.Children)
	}
}

func (s *SubredditMonitor) checkAndStoreComment(comment *reddit.Comment) {
	isNew := store.InsertRedisComment(s.subreddit, comment, s.rdb)
	if isNew && comment.PostTitle == "" {
		channel := s.commentsSource.CommentChannel()
		channel <- comment
	}
}

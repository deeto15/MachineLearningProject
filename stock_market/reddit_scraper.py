import asyncio
import sqlite3
import time
from datetime import datetime, timezone

import praw


# Initialize the database and create tables
def initialize_db(db_path="/vault/reddit_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Table for posts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            postID TEXT PRIMARY KEY,
            title TEXT,
            body TEXT,
            score INTEGER,
            upvote_ratio REAL,
            total_comments INTEGER,
            created_on INTEGER,
            url TEXT,
            original_content BOOLEAN
        )
    """)
    # Table for comments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            commentID TEXT PRIMARY KEY,
            body TEXT,
            time INTEGER,
            postID TEXT,
            FOREIGN KEY (postID) REFERENCES posts(postID)
        )
    """)
    # Table for seen post IDs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_posts (
            postID TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


# Load seen IDs from the database
def load_seen_ids(db_path="/app/data/reddit_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT postID FROM seen_posts")
    seen_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return seen_ids


# Save seen IDs to the database
def save_seen_ids(new_ids, db_path="/app/data/reddit_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT OR IGNORE INTO seen_posts (postID) VALUES (?)",
        ((post_id,) for post_id in new_ids),
    )
    conn.commit()
    conn.close()


# Save posts to the database
def save_posts_to_db(posts_dict, db_path="/app/data/reddit_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR IGNORE INTO posts (postID, title, body, score, upvote_ratio, total_comments, created_on, url, original_content)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        [
            (
                posts_dict["ID"][i],
                posts_dict["Title"][i],
                posts_dict["Post Text"][i],
                posts_dict["Score"][i],
                posts_dict["Upvote Ratio"][i],
                posts_dict["Total Comments"][i],
                posts_dict["Created On"][i],
                posts_dict["Post URL"][i],
                posts_dict["Original Content"][i],
            )
            for i in range(len(posts_dict["ID"]))
        ],
    )
    conn.commit()
    conn.close()


# Get all post IDs from the posts table
def get_post_ids_from_db(db_path="/app/data/reddit_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT postID FROM seen_posts")
    post_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return post_ids


# Save comments to the database
def write_batch_to_db(batch_comments, db_path="/app/data/reddit_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR IGNORE INTO comments (commentID, body, time, postID)
        VALUES (:commentID, :body, :time, :postID)
    """,
        batch_comments,
    )
    conn.commit()
    conn.close()


# Handle Reddit rate limits
def handle_rate_limit(reddit_client):
    rate_limit_info = reddit_client.auth.limits
    remaining_requests = rate_limit_info.get("remaining", 60)
    reset_time = rate_limit_info.get("reset_timestamp", time.time() + 60)
    if remaining_requests < 5:  # Safety threshold
        sleep_time = reset_time - time.time() + 1  # Add buffer
        if sleep_time > 0:
            print(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)


# Scrape posts and save to the database
async def post_scraper(reddit_client, subreddit_name="wallstreetbets"):
    initialize_db()
    seen_ids = load_seen_ids()
    print(len(seen_ids))
    subreddit = reddit_client.subreddit(subreddit_name)
    posts = subreddit.top(time_filter="all", limit=None)

    posts_dict = {
        "Title": [],
        "Post Text": [],
        "ID": [],
        "Score": [],
        "Upvote Ratio": [],
        "Total Comments": [],
        "Created On": [],
        "Post URL": [],
        "Original Content": [],
    }
    new_ids = set()

    for post in posts:
        handle_rate_limit(reddit_client)  # Ensure we don't hit rate limits
        if post.id not in seen_ids:
            posts_dict["Title"].append(post.title)
            posts_dict["Post Text"].append(post.selftext)
            posts_dict["ID"].append(post.id)
            posts_dict["Score"].append(post.score)
            posts_dict["Upvote Ratio"].append(post.upvote_ratio)
            posts_dict["Total Comments"].append(post.num_comments)
            posts_dict["Created On"].append(post.created_utc)
            posts_dict["Post URL"].append(post.url)
            posts_dict["Original Content"].append(post.is_original_content)
            new_ids.add(post.id)

    save_posts_to_db(posts_dict)
    save_seen_ids(new_ids)


# Fetch and process comments for each post
async def fetch_all_comments(reddit_client, db_path="/app/data/reddit_data.db"):
    # initialize_db()
    post_ids = get_post_ids_from_db()
    print(len(post_ids))
    for post_id in post_ids:
        # handle_rate_limit(reddit_client)
        try:
            print(f"Fetching comments for post ID: {post_id}")
            submission = reddit_client.submission(id=post_id)
            submission.comment_sort = "new"

            await asyncio.to_thread(submission.comments.replace_more, limit=None)
            comment_queue = submission.comments[:]
            batch_comments = []

            while comment_queue:
                current_batch = comment_queue[:300]
                comment_queue = comment_queue[300:]

                for comment in current_batch:
                    if isinstance(
                        comment, praw.models.Submission
                    ):  # Check if it's the post itself
                        batch_comments.append(
                            {
                                "commentID": comment.id,
                                "body": comment.selftext,
                                "time": int(comment.created_utc),
                                "postID": comment.id,  # Post is its own parent
                            }
                        )
                    elif isinstance(comment, praw.models.Comment):
                        batch_comments.append(
                            {
                                "commentID": comment.id,
                                "body": comment.body,
                                "time": int(comment.created_utc),
                                "postID": post_id,
                            }
                        )
                        comment_queue.extend(comment.replies)

                print(
                    f"Processed {len(batch_comments)} comments for post ID: {post_id}."
                )
                write_batch_to_db(batch_comments, db_path)
                batch_comments = []

        except Exception as e:
            print(f"Error fetching comments for post ID {post_id}: {e}")
            await asyncio.sleep(5)

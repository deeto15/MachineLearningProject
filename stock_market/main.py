import os
import time
import json
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
import praw

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT")
)
conn.autocommit = True
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY,
    title TEXT,
    selftext TEXT,
    author TEXT,
    created_utc DOUBLE PRECISION,
    num_comments INTEGER,
    score INTEGER,
    upvote_ratio DOUBLE PRECISION,
    url TEXT,
    permalink TEXT,
    subreddit TEXT,
    over_18 BOOLEAN,
    stickied BOOLEAN,
    locked BOOLEAN,
    is_self BOOLEAN,
    is_video BOOLEAN,
    domain TEXT,
    media JSONB,
    preview JSONB,
    last_updated_utc DOUBLE PRECISION
)
''')

subreddit = reddit.subreddit('wallstreetbets')

for submission in subreddit.new(limit=None):
    c.execute('SELECT created_utc FROM posts WHERE post_id = %s', (submission.id,))
    existing = c.fetchone()

    media_json = json.dumps(getattr(submission, 'media', None)) if getattr(submission, 'media', None) else None
    preview_json = json.dumps(getattr(submission, 'preview', None)) if getattr(submission, 'preview', None) else None

    if existing is None:
        c.execute('''
            INSERT INTO posts (post_id, title, selftext, author, created_utc, num_comments, score,
                               upvote_ratio, url, permalink, subreddit, over_18, stickied, locked,
                               is_self, is_video, domain, media, preview, last_updated_utc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            submission.id,
            submission.title,
            submission.selftext,
            str(submission.author) if submission.author else None,
            submission.created_utc,
            submission.num_comments,
            submission.score,
            submission.upvote_ratio,
            submission.url,
            submission.permalink,
            str(submission.subreddit),
            submission.over_18,
            submission.stickied,
            submission.locked,
            submission.is_self,
            submission.is_video,
            submission.domain,
            media_json,
            preview_json,
            time.time()
        ))
    else:
        post_age = datetime.utcnow() - datetime.utcfromtimestamp(existing[0])
        if post_age <= timedelta(weeks=1):
            c.execute('''
                UPDATE posts
                SET title = %s, selftext = %s, author = %s, num_comments = %s, score = %s, upvote_ratio = %s,
                    url = %s, permalink = %s, subreddit = %s, over_18 = %s, stickied = %s, locked = %s,
                    is_self = %s, is_video = %s, domain = %s, media = %s, preview = %s, last_updated_utc = %s
                WHERE post_id = %s
            ''', (
                submission.title,
                submission.selftext,
                str(submission.author) if submission.author else None,
                submission.num_comments,
                submission.score,
                submission.upvote_ratio,
                submission.url,
                submission.permalink,
                str(submission.subreddit),
                submission.over_18,
                submission.stickied,
                submission.locked,
                submission.is_self,
                submission.is_video,
                submission.domain,
                media_json,
                preview_json,
                time.time(),
                submission.id
            ))

    time.sleep(2)

c.close()
conn.close()

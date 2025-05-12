class FakeComment:
    def __init__(self, id, author, body, created_utc, score, parent_id, is_submitter, permalink):
        self.id = id
        self.author = author
        self.body = body
        self.created_utc = created_utc
        self.score = score
        self.parent_id = parent_id
        self.is_submitter = is_submitter
        self.permalink = permalink


import os
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

DB_PARAMS = {
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "database": os.getenv("POSTGRES_DB"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
}


async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS posts(
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
                last_updated_utc DOUBLE PRECISION,
                last_checked_utc DOUBLE PRECISION
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS comments(
                comment_id TEXT PRIMARY KEY,
                post_id TEXT REFERENCES posts(post_id),
                author TEXT,
                body TEXT,
                created_utc DOUBLE PRECISION,
                score INTEGER,
                parent_id TEXT,
                is_submitter BOOLEAN,
                permalink TEXT,
                last_updated_utc DOUBLE PRECISION,
                extracted_stock TEXT,
                extracted_price TEXT,
                extracted_date TEXT
            )
        """)

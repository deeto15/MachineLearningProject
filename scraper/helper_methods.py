import os
from dotenv import load_dotenv

class FakeComment:
    def __init__(
        self, id, author, body, created_utc, score, parent_id, is_submitter, permalink
    ):
        self.id = id
        self.author = author
        self.body = body
        self.created_utc = created_utc
        self.score = score
        self.parent_id = parent_id
        self.is_submitter = is_submitter
        self.permalink = permalink

    def __repr__(self):
        return f"FakeComment(id='{self.id}', body='{self.body[:30]}...')"

load_dotenv()
REDDIT_PARAMS = {
    "client_id": os.getenv("REDDIT_CLIENT_ID"),
    "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
    "username": os.getenv("REDDIT_USERNAME"),
    "password": os.getenv("REDDIT_PASSWORD"),
    "user_agent": os.getenv("REDDIT_USER_AGENT"),
}

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
                extracted_stock TEXT,
                extracted_price TEXT,
                extracted_date TEXT
            )
        """)


INSERT_COMMENTS = (
    """
                    INSERT INTO comments (
                        comment_id, post_id, author, body, created_utc,
                        score, parent_id, is_submitter, permalink,
                        extracted_stock, extracted_price, extracted_date
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12
                    ) ON CONFLICT (comment_id) DO UPDATE SET
                        score = EXCLUDED.score,
                        extracted_stock = EXCLUDED.extracted_stock,
                        extracted_price = EXCLUDED.extracted_price,
                        extracted_date = EXCLUDED.extracted_date
                """
)

INSERT_POSTS = (
    """
                INSERT INTO posts (
                    post_id, title, selftext, author, created_utc,
                    num_comments, score, upvote_ratio, url, permalink,
                    subreddit, over_18, stickied, locked,
                    is_self, is_video, domain, media, preview,
                    last_checked_utc
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                    $11,$12,$13,$14,$15,$16,$17,$18,$19,$20
                ) ON CONFLICT (post_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    selftext = EXCLUDED.selftext,
                    author = EXCLUDED.author,
                    num_comments = EXCLUDED.num_comments,
                    score = EXCLUDED.score,
                    upvote_ratio = EXCLUDED.upvote_ratio,
                    url = EXCLUDED.url,
                    permalink = EXCLUDED.permalink,
                    subreddit = EXCLUDED.subreddit,
                    over_18 = EXCLUDED.over_18,
                    stickied = EXCLUDED.stickied,
                    locked = EXCLUDED.locked,
                    is_self = EXCLUDED.is_self,
                    is_video = EXCLUDED.is_video,
                    domain = EXCLUDED.domain,
                    media = EXCLUDED.media,
                    preview = EXCLUDED.preview,
                    last_checked_utc = EXCLUDED.last_checked_utc
            """
)


INSERT_NEW_POSTS = (
    """
    INSERT INTO posts (
        post_id, title, selftext, author, created_utc,
        num_comments, score, upvote_ratio, url, permalink,
        subreddit, over_18, stickied, locked,
        is_self, is_video, domain, media, preview,
        last_checked_utc
    ) VALUES (
        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
        $11,$12,$13,$14,$15,$16,$17,$18,$19,$20
    ) ON CONFLICT (post_id) DO NOTHING
    """
)
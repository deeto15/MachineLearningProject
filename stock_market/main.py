import os
import time
import json
import asyncio
import traceback
import asyncpraw
import asyncpg
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import asyncprawcore

load_dotenv()
reddit_semaphore = asyncio.Semaphore(5)

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


def safe_json(obj, attr):
    val = getattr(obj, attr, None)
    return json.dumps(val) if val is not None else None


async def safe_replace_more(comments, limit, retries=5):
    delay = 2
    for _ in range(retries):
        try:
            await comments.replace_more(limit=limit)
            return
        except asyncprawcore.exceptions.TooManyRequests:
            await asyncio.sleep(delay)
            delay *= 2


async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
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
            last_updated_utc DOUBLE PRECISION,
            last_checked_utc DOUBLE PRECISION
        )""")
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT REFERENCES posts(post_id),
            author TEXT,
            body TEXT,
            created_utc DOUBLE PRECISION,
            score INTEGER,
            parent_id TEXT,
            is_submitter BOOLEAN,
            permalink TEXT,
            last_updated_utc DOUBLE PRECISION
        )""")


async def batch_insert_posts(pool, submissions):
    async with pool.acquire() as conn:
        now = time.time()
        records = []
        for s in submissions:
            records.append(
                (
                    s.id,
                    s.title,
                    s.selftext,
                    s.author.name if s.author else None,
                    s.created_utc,
                    s.num_comments,
                    s.score,
                    s.upvote_ratio,
                    s.url,
                    s.permalink,
                    str(s.subreddit),
                    s.over_18,
                    s.stickied,
                    s.locked,
                    s.is_self,
                    s.is_video,
                    s.domain,
                    safe_json(s, "media"),
                    safe_json(s, "preview"),
                    now,
                    now,
                )
            )
        await conn.executemany(
            """
        INSERT INTO posts (
            post_id, title, selftext, author, created_utc, num_comments, score,
            upvote_ratio, url, permalink, subreddit, over_18, stickied, locked,
            is_self, is_video, domain, media, preview, last_updated_utc, last_checked_utc
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
            $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
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
            last_updated_utc = EXCLUDED.last_updated_utc,
            last_checked_utc = EXCLUDED.last_checked_utc
        """,
            records,
        )


async def batch_insert_comments(pool, submission):
    try:
        await submission.load()
        async with reddit_semaphore:
            await safe_replace_more(submission.comments, limit=32)
        all_comments_raw = await submission.comments.list()
        now = time.time()
        records = []
        real_comment_count = 0
        for c in all_comments_raw:
            if isinstance(c, asyncpraw.models.MoreComments):
                continue
            if not c.id:
                continue
            real_comment_count += 1
            records.append(
                (
                    c.id,
                    submission.id,
                    c.author.name if c.author else None,
                    c.body,
                    c.created_utc,
                    c.score,
                    c.parent_id,
                    c.is_submitter,
                    c.permalink,
                    now,
                )
            )

        print(f"Post {submission.id}: expanded to {real_comment_count} real comments")

        if records:
            async with pool.acquire() as conn:
                await conn.executemany(
                    """
                INSERT INTO comments (
                    comment_id, post_id, author, body, created_utc,
                    score, parent_id, is_submitter, permalink, last_updated_utc
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
                ) ON CONFLICT (comment_id) DO UPDATE SET
                    score = EXCLUDED.score,
                    last_updated_utc = EXCLUDED.last_updated_utc
                """,
                    records,
                )
            print(
                f"Post {submission.id}: inserted {len(records)} comments into database"
            )
        else:
            print(f"Post {submission.id}: no comments to insert")

    except asyncprawcore.exceptions.NotFound:
        print(f"Post {submission.id} was deleted or removed")
    except asyncprawcore.exceptions.Forbidden:
        print(f"Post {submission.id} is forbidden (maybe locked or private)")
    except Exception as e:
        print(f"Error inserting comments for {submission.id}: {e}")


async def update_existing_posts(pool, reddit):
    async with pool.acquire() as conn:
        now = time.time()
        rows = await conn.fetch(
            """
        SELECT post_id FROM posts
        WHERE created_utc > $1 AND (
            last_checked_utc IS NULL OR
            (
                (created_utc > $2 AND $3 - last_checked_utc >= $4) OR
                (created_utc > $5 AND $3 - last_checked_utc >= $6) OR
                (created_utc > $7 AND $3 - last_checked_utc >= $8)
            )
        )
        """,
            now - 2592000,
            now - 86400,
            now,
            3600,
            now - 604800,
            43200,
            now - 2592000,
            86400,
        )
    ids = [r["post_id"] for r in rows]
    for i in range(0, len(ids), 100):
        batch_ids = ids[i : i + 100]
        attempts = 3
        for attempt in range(attempts):
            try:
                submissions = [
                    s
                    async for s in reddit.info(
                        fullnames=[f"t3_{pid}" for pid in batch_ids]
                    )
                ]
                if not submissions:
                    print(
                        "Warning: No submissions returned. Possible shadowban or throttling."
                    )
                await batch_insert_posts(pool, submissions)
                await asyncio.gather(
                    *(batch_insert_comments(pool, s) for s in submissions)
                )
                break
            except asyncprawcore.exceptions.TooManyRequests:
                wait_time = 2**attempt
                print(f"Rate limited. Sleeping {wait_time}s.")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"Error updating posts batch: {e}")
                traceback.print_exc()
                await asyncio.sleep(2)
    print("Finished update_existing_posts")


async def scrape_new_posts(pool, subreddit):
    print("Starting scrape_new_posts")
    seen = set()
    ids = []
    posts = []
    listing_types = ["new", "rising", "top", "hot"]
    for listing in listing_types:
        try:
            async for s in getattr(subreddit, listing)(limit=1000):
                if s.id in seen:
                    continue
                seen.add(s.id)
                ids.append(s.id)
                posts.append(s)
        except Exception as e:
            print(f"Error fetching from listing {listing}: {e}")

    print(f"Fetched {len(posts)} unique posts from listings")

    async with pool.acquire() as conn:
        existing_rows = await conn.fetch(
            "SELECT post_id, created_utc, last_checked_utc FROM posts WHERE post_id = ANY($1)",
            ids,
        )
        existing_map = {
            r["post_id"]: {
                "created_utc": r["created_utc"],
                "last_checked_utc": r["last_checked_utc"] or 0,
            }
            for r in existing_rows
        }

    now_ts = time.time()
    filtered = []
    for s in posts:
        record = existing_map.get(s.id)
        if record is None:
            filtered.append(s)
            continue

        age = now_ts - record["created_utc"]
        since_checked = now_ts - record["last_checked_utc"]

        if age <= 86400 and since_checked >= 900:
            filtered.append(s)
        elif age <= 604800 and since_checked >= 7200:
            filtered.append(s)
        elif age <= 2592000 and since_checked >= 43200:
            filtered.append(s)

    print(f"{len(filtered)} posts to insert or update")

    await batch_insert_posts(pool, filtered)
    for s in filtered:
        try:
            await batch_insert_comments(pool, s)
        except Exception as e:
            print(f"Post {s.id} failed to insert comments: {e}")

    total_expected_comments = sum(
        s.num_comments for s in filtered if s.num_comments is not None
    )

    async with pool.acquire() as conn:
        actual_count = await conn.fetchval(
            "SELECT COUNT(*) FROM comments WHERE post_id = ANY($1)",
            [s.id for s in filtered],
        )

    print(f"Expected total comments from Reddit metadata: {total_expected_comments}")
    print(f"Actual comments inserted in DB: {actual_count}")


async def main():
    reddit = asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
        user_agent=REDDIT_USER_AGENT,
    )
    pool = await asyncpg.create_pool(**DB_PARAMS)
    try:
        try:
            me = await reddit.user.me()
            print(f"Authenticated as: {me.name}")
        except Exception as e:
            print(
                "Failed to fetch user profile. Possibly shadowbanned or bad credentials."
            )
            import traceback

            traceback.print_exc()

        await create_tables(pool)
        subreddit = await reddit.subreddit("wallstreetbets")
        await update_existing_posts(pool, reddit)
        await scrape_new_posts(pool, subreddit)
    finally:
        await reddit.close()
        await pool.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")

import os
import time
import json
import asyncio
import random
import traceback
import asyncpraw
import asyncpg
import asyncprawcore
from dotenv import load_dotenv

load_dotenv()
reddit_semaphore = asyncio.Semaphore(2)
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


async def retry_api_call(coro, retries=5):
    delay = 2
    for _ in range(retries):
        try:
            return await coro
        except asyncprawcore.exceptions.TooManyRequests:
            await asyncio.sleep(delay + random.uniform(0, 1))
            delay *= 2
        except Exception as e:
            print("retry_api_call caught", type(e).__name__, e)
            await asyncio.sleep(1 + random.uniform(0, 2))
    raise RuntimeError("retry_api_call failed after retries")


async def safe_replace_more(comments, limit):
    await retry_api_call(comments.replace_more(limit=limit))


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
            )
        """)
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
            )
        """)


async def batch_insert_posts(pool, submissions):
    now = time.time()
    records = [
        (
            s.id,
            s.title,
            s.selftext,
            getattr(s.author, "name", None),
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
        for s in submissions
    ]
    async with pool.acquire() as conn:
        for i in range(0, len(records), 500):
            await conn.executemany(
                """
                INSERT INTO posts (
                    post_id, title, selftext, author, created_utc,
                    num_comments, score, upvote_ratio, url, permalink,
                    subreddit, over_18, stickied, locked,
                    is_self, is_video, domain, media, preview,
                    last_updated_utc, last_checked_utc
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                    $11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21
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
                records[i : i + 500],
            )
            await asyncio.sleep(random.uniform(0.5, 1.5))


async def upsert_posts_for_update(pool, submissions):
    now = time.time()
    records = [
        (
            s.id,
            s.title,
            s.selftext,
            getattr(s.author, "name", None),
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
        )
        for s in submissions
    ]
    async with pool.acquire() as conn:
        for i in range(0, len(records), 500):
            await conn.executemany(
                """
                INSERT INTO posts (
                    post_id, title, selftext, author, created_utc,
                    num_comments, score, upvote_ratio, url, permalink,
                    subreddit, over_18, stickied, locked,
                    is_self, is_video, domain, media, preview,
                    last_updated_utc
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
                    last_updated_utc = EXCLUDED.last_updated_utc
            """,
                records[i : i + 500],
            )
            await asyncio.sleep(random.uniform(0.5, 1.5))


async def batch_insert_comments(pool, submission):
    try:
        await submission.load()
        async with reddit_semaphore:
            await safe_replace_more(submission.comments, limit=32)
        all_comments = submission.comments.list()
        now = time.time()
        records = []
        for c in all_comments:
            if not hasattr(c, "id") or isinstance(c, asyncpraw.models.MoreComments):
                continue
            records.append(
                (
                    c.id,
                    submission.id,
                    getattr(c.author, "name", None),
                    c.body,
                    c.created_utc,
                    c.score,
                    c.parent_id,
                    c.is_submitter,
                    c.permalink,
                    now,
                )
            )
        async with pool.acquire() as conn:
            for i in range(0, len(records), 500):
                await conn.executemany(
                    """
                    INSERT INTO comments (
                        comment_id, post_id, author, body, created_utc,
                        score, parent_id, is_submitter, permalink, last_updated_utc
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10
                    ) ON CONFLICT (comment_id) DO UPDATE SET
                        score = EXCLUDED.score,
                        last_updated_utc = EXCLUDED.last_updated_utc
                """,
                    records[i : i + 500],
                )
                await asyncio.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        print(f"Post {submission.id} failed to insert comments: {e}")


async def fetch_submissions(reddit, fullnames):
    gen = reddit.info(fullnames=fullnames)
    return [s async for s in gen]


async def update_existing_posts(pool, reddit):
    print("Starting update_existing_posts")

    # 1) fetch IDs that need checking
    async with pool.acquire() as conn:
        now = time.time()
        rows = await conn.fetch(
            """
            SELECT post_id
              FROM posts
             WHERE created_utc > $1
               AND (
                     last_checked_utc IS NULL
                  OR (
                       (created_utc > $2 AND $3 - last_checked_utc >= $4)
                    OR (created_utc > $5 AND $3 - last_checked_utc >= $6)
                    OR (created_utc > $7 AND $3 - last_checked_utc >= $8)
                   )
               )
            """,
            now - 2592000,  # 30d
            now - 86400,  # 1d
            now,
            3600,  # hourly for <1d
            now - 604800,  # 7d
            43200,  # every 12h for <7d
            now - 2592000,  # 30d
            86400,  # every 24h for <30d
        )
    ids = [r["post_id"] for r in rows]
    print(f"Found {len(ids)} posts to update")

    total_expected = 0
    total_inserted = 0

    # 2) process in batches of 100
    for batch_index in range(0, len(ids), 100):
        batch_ids = ids[batch_index : batch_index + 100]
        fullnames = [f"t3_{pid}" for pid in batch_ids]

        try:
            # 3) fetch & upsert metadata only
            submissions = await retry_api_call(fetch_submissions(reddit, fullnames))
            if not submissions:
                continue
            await upsert_posts_for_update(pool, submissions)

            # 4) per-post: insert comments, then mark checked
            for s in submissions:
                total_expected += s.num_comments or 0

                await batch_insert_comments(pool, s)

                async with pool.acquire() as conn:
                    # mark this post as fully checked
                    await conn.execute(
                        "UPDATE posts SET last_checked_utc = $1 WHERE post_id = $2",
                        time.time(),
                        s.id,
                    )
                    # count inserted comments
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM comments WHERE post_id = $1", s.id
                    )

                total_inserted += count
                print(f"✅ Post {s.id}: inserted {count}/{s.num_comments} comments")

        except asyncprawcore.exceptions.TooManyRequests:
            # exponential back-off on rate limits
            delay = 2 ** (batch_index // 100 + 1)
            print(f"Rate limited in batch {batch_index // 100 + 1}, sleeping {delay}s")
            await asyncio.sleep(delay)
        except Exception as e:
            print(
                f"❌ Error in batch {batch_index // 100 + 1}: {type(e).__name__}: {e}"
            )
            traceback.print_exc()
            await asyncio.sleep(2)

    print("Finished update_existing_posts")
    print(f"Expected comments: {total_expected}")
    print(f"Inserted comments: {total_inserted}")


async def scrape_new_posts(pool, subreddit):
    print("Starting scrape_new_posts")

    # 1) pull down listings
    seen, ids, posts = set(), [], []
    for listing in ["new", "rising", "top", "hot"]:
        try:
            async for s in getattr(subreddit, listing)(limit=1000):
                if s.id not in seen:
                    seen.add(s.id)
                    ids.append(s.id)
                    posts.append(s)
        except Exception as e:
            print(f"Error fetching from listing {listing}: {e}")

    print(f"Fetched {len(posts)} unique posts from listings")

    # 2) find which ones need processing
    async with pool.acquire() as conn:
        existing = await conn.fetch(
            "SELECT post_id, created_utc, last_checked_utc "
            "FROM posts WHERE post_id = ANY($1)",
            ids,
        )
    existing_map = {
        r["post_id"]: {
            "created_utc": r["created_utc"],
            "last_checked_utc": r["last_checked_utc"] or 0,
        }
        for r in existing
    }

    now_ts = time.time()
    filtered = []
    for s in posts:
        rec = existing_map.get(s.id)
        age = now_ts - (rec["created_utc"] if rec else 0)
        since = now_ts - (rec["last_checked_utc"] if rec else 0)

        # your three time‐based rules
        if (
            not rec
            or (age <= 86400 and since >= 900)
            or (age <= 604800 and since >= 7200)
            or (age <= 2592000 and since >= 43200)
        ):
            filtered.append(s)

    print(f"{len(filtered)} posts to insert or update")

    # 3) upsert **only** metadata (no last_checked_utc)
    await upsert_posts_for_update(pool, filtered)

    # 4) per‐post: insert comments, then mark it checked
    total_expected = 0
    total_inserted = 0

    for s in filtered:
        try:
            total_expected += s.num_comments or 0

            # insert all comments for this one post
            await batch_insert_comments(pool, s)

            # mark this post as fully checked
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE posts SET last_checked_utc = $1 WHERE post_id = $2",
                    time.time(),
                    s.id,
                )

            # tally how many comments actually landed
            async with pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM comments WHERE post_id = $1", s.id
                )
            total_inserted += count

            print(f"✅ Scraped {count}/{s.num_comments} comments for post {s.id}")

        except Exception as e:
            # on any failure we do *not* update last_checked_utc,
            # so next run we'll retry exactly this post
            print(f"❌ Failed processing post {s.id}: {e}")
            traceback.print_exc()

    print(f"Expected comments: {total_expected}")
    print(f"Inserted comments: {total_inserted}")


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
        await reddit.user.me()
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

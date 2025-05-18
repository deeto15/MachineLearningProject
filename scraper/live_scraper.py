from collections import Counter
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
from Binary_Classifier.BERT_loader import load_model
from Binary_Classifier.predictions import tokens
from scraper.helper_methods import (
    INSERT_COMMENTS,
    INSERT_POSTS,
    create_tables,
    FakeComment,
    DB_PARAMS,
    REDDIT_PARAMS,
)


load_dotenv()
reddit_semaphore = asyncio.Semaphore(2)


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
            now
        )
        for s in submissions
    ]
    async with pool.acquire() as conn:
        for i in range(0, len(records), 500):
            await conn.executemany(INSERT_POSTS, records[i:i+500])
            await asyncio.sleep(random.uniform(0.5,1.5))

pipeline = load_model()


async def batch_insert_comments(pool, submission):
    try:
        await submission.load()
        async with reddit_semaphore:
            await safe_replace_more(submission.comments, limit=256)
        comments = [
            c
            for c in submission.comments.list()
            if hasattr(c, "id") and not isinstance(c, asyncpraw.models.MoreComments)
        ]
        print(f"scraped {len(comments)} comments for post {submission.id}")

        ner_list = []
        combined = submission.title + "\n\n" + submission.selftext
        fake = FakeComment(
            submission.id,
            submission.author,
            combined,
            submission.created_utc,
            submission.score,
            f"t3_{submission.id}",
            True,
            submission.permalink,
        )
        ner = tokens(fake.body)
        if ner:
            ner_list.append((fake, ner))
        for c in comments:
            ner = tokens(c.body)
            if ner:
                ner_list.append((c, ner))
        print(f"{len(ner_list)} items passed NER")

        if not ner_list:
            return
        texts = [c.body for c, _ in ner_list]
        print(texts)
        preds, _ = await asyncio.get_event_loop().run_in_executor(
            None, lambda: pipeline.predict_batch(texts, batch_size=32)
        )
        print(f"classifier output counts: {Counter(preds)}")

        valid = [(c, ner) for (c, ner), p in zip(ner_list, preds) if p == 1]
        print(f"{len(valid)} comments passed classification")
        print(valid)

        if not valid:
            return

        records = [
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
                ner["Stock"],
                ner["Price"],
                ner["Date"],
            )
            for c, ner in valid
        ]

        async with pool.acquire() as conn:
            for i in range(0, len(records), 500):
                await conn.executemany(
                    INSERT_COMMENTS,
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
            submissions = await retry_api_call(fetch_submissions(reddit, fullnames))
            if not submissions:
                continue

            # Instead of upserting all posts at once, do it per post:
            for s in submissions:
                await upsert_posts_for_update(pool, [s])  # upsert one post
                total_expected += s.num_comments or 0

                await batch_insert_comments(pool, s)

                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE posts SET last_checked_utc = $1 WHERE post_id = $2",
                        time.time(),
                        s.id,
                    )
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
    MAX_AGE = 30 * 86400
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
            not rec and age <= MAX_AGE
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


async def run_live_scraper():
    reddit = asyncpraw.Reddit(**REDDIT_PARAMS)
    pool = await asyncpg.create_pool(**DB_PARAMS)
    try:
        await reddit.user.me()
        await create_tables(pool)
        subreddit = await reddit.subreddit("wallstreetbets")
        await scrape_new_posts(pool, subreddit)
        await update_existing_posts(pool, reddit)
    finally:
        await reddit.close()
        await pool.close()

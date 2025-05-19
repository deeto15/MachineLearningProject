import time
import json
import asyncpg
from dotenv import load_dotenv
from Binary_Classifier.BERT_loader import load_model
from Binary_Classifier.predictions import tokens
from scraper.helper_methods import INSERT_COMMENTS, INSERT_NEW_POSTS, create_tables, DB_PARAMS
load_dotenv()

POSTS_FILE = r"C:\Users\Kendall Eberly\Downloads\wallstreetbets_submissions\wallstreetbets_submissions"
COMMENTS_FILE = (
    r"C:\Users\Kendall Eberly\Downloads\wallstreetbets_comments\wallstreetbets_comments"
)
CATCH_ALL_ID = "__CATCH_ALL__"


def clean_str(s):
    return s.replace("\x00", "") if isinstance(s, str) else s


def stream_items(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


pipeline = load_model()


async def batch_insert_posts(pool, records):
    now = time.time()
    vals = []
    for r in records:
        vals.append(
            (
                clean_str(r.get("id")),
                clean_str(r.get("title")),
                clean_str(r.get("selftext")),
                clean_str(r.get("author")),
                float(r.get("created_utc") or 0),
                int(r.get("num_comments") or 0),
                int(r.get("score") or 0),
                float(r.get("upvote_ratio") or 0),
                clean_str(r.get("url")),
                clean_str(r.get("permalink")),
                clean_str(r.get("subreddit")),
                bool(r.get("over_18")),
                bool(r.get("stickied")),
                bool(r.get("locked")),
                bool(r.get("is_self")),
                bool(r.get("is_video")),
                clean_str(r.get("domain")),
                json.dumps(r.get("media")) if r.get("media") else None,
                json.dumps(r.get("preview")) if r.get("preview") else None,
                now,
            )
        )
    async with pool.acquire() as conn:
        for i in range(0, len(vals), 500):
            await conn.executemany(INSERT_NEW_POSTS, vals[i : i + 500])


async def insert_catch_all(pool):
    now = time.time()
    async with pool.acquire() as conn:
        await conn.execute(
            INSERT_NEW_POSTS,
            CATCH_ALL_ID,
            "",
            "",
            "",
            0.0,
            0,
            0,
            0.0,
            "",
            "",
            "",
            False,
            False,
            False,
            False,
            False,
            "",
            None,
            None,
            now,
        )


async def batch_insert_comments(pool, records):
    ner_list = []
    for r in records:
        body = clean_str(r.get("body"))
        ner = tokens(body)
        if ner:
            ner_list.append((r, ner))
    if not ner_list:
        return
    texts = [clean_str(r["body"]) for r, _ in ner_list]
    preds, _ = pipeline.predict_batch(texts, batch_size=32)
    valid = [(r, ner) for (r, ner), p in zip(ner_list, preds) if p == 1]
    if not valid:
        return

    def get_post_id_from_comment(r):
        link_id = r.get("link_id")
        if link_id and link_id.startswith("t3_"):
            return link_id[3:]
        if r.get("post_id"):
            return r.get("post_id")
        return None

    batch_post_ids = [get_post_id_from_comment(r) for r, _ in valid]
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT post_id FROM posts WHERE post_id = ANY($1)", batch_post_ids
        )
        existing = {row["post_id"] for row in rows}
        vals = []
        for r, ner in valid:
            pid = get_post_id_from_comment(r)
            if pid not in existing:
                pid = CATCH_ALL_ID
            vals.append(
                (
                    clean_str(r.get("id")),
                    pid,
                    clean_str(r.get("author")),
                    clean_str(r.get("body")),
                    float(r.get("created_utc") or 0),
                    int(r.get("score") or 0),
                    clean_str(r.get("parent_id")),
                    bool(r.get("is_submitter")),
                    clean_str(r.get("permalink")),
                    ner["Stock"],
                    ner["Price"],
                    ner["Date"],
                )
            )
        for i in range(0, len(vals), 500):
            await conn.executemany(INSERT_COMMENTS, vals[i : i + 500])



async def import_posts(pool):
    batch = []
    print("Importing posts...")
    for post in stream_items(POSTS_FILE):
        batch.append(post)
        if len(batch) >= 500:
            await batch_insert_posts(pool, batch)
            batch.clear()
    if batch:
        await batch_insert_posts(pool, batch)
    print("Importing posts done.")


async def import_comments(pool):
    print("Importing comments...")
    batch = []
    for comment in stream_items(COMMENTS_FILE):
        batch.append(comment)
        if len(batch) >= 500:
            await batch_insert_comments(pool, batch)
            batch.clear()
    if batch:
        await batch_insert_comments(pool, batch)
    print("Importing comments done.")


async def run_past_scraper():
    pool = await asyncpg.create_pool(**DB_PARAMS)
    await create_tables(pool)
    await insert_catch_all(pool)
    await import_posts(pool)
    await import_comments(pool)
    await pool.close()

#TODO add posts to fakecomment when processing comments
#TODO find a way to keep going if you stop the program mid run, maybe check last id and scan forward until then?
#TODO retrain model with items missing from stockname

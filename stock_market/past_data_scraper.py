import os
import time
import json
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DB_PARAMS={
    'user':os.getenv('POSTGRES_USER'),
    'password':os.getenv('POSTGRES_PASSWORD'),
    'database':os.getenv('POSTGRES_DB'),
    'host':os.getenv('POSTGRES_HOST'),
    'port':os.getenv('POSTGRES_PORT')
}
POSTS_FILE=r"C:\Users\Kendall Eberly\Downloads\wallstreetbets_submissions\wallstreetbets_submissions"
COMMENTS_FILE=r"C:\Users\Kendall Eberly\Downloads\wallstreetbets_comments\wallstreetbets_comments"

def clean_str(s):
    return s.replace('\x00','') if isinstance(s,str) else s

async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS posts(post_id TEXT PRIMARY KEY,title TEXT,selftext TEXT,author TEXT,created_utc DOUBLE PRECISION,num_comments INTEGER,score INTEGER,upvote_ratio DOUBLE PRECISION,url TEXT,permalink TEXT,subreddit TEXT,over_18 BOOLEAN,stickied BOOLEAN,locked BOOLEAN,is_self BOOLEAN,is_video BOOLEAN,domain TEXT,media JSONB,preview JSONB,last_updated_utc DOUBLE PRECISION,last_checked_utc DOUBLE PRECISION)"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS comments(comment_id TEXT PRIMARY KEY,post_id TEXT REFERENCES posts(post_id),author TEXT,body TEXT,created_utc DOUBLE PRECISION,score INTEGER,parent_id TEXT,is_submitter BOOLEAN,permalink TEXT,last_updated_utc DOUBLE PRECISION)"
        )

async def batch_insert_posts(pool,records):
    now=time.time()
    vals=[]
    for r in records:
        vals.append((
            clean_str(r.get('id')),
            clean_str(r.get('title')),
            clean_str(r.get('selftext')),
            clean_str(r.get('author')),
            float(r.get('created_utc') or 0),
            int(r.get('num_comments') or 0),
            int(r.get('score') or 0),
            float(r.get('upvote_ratio') or 0),
            clean_str(r.get('url')),
            clean_str(r.get('permalink')),
            clean_str(r.get('subreddit')),
            bool(r.get('over_18')),
            bool(r.get('stickied')),
            bool(r.get('locked')),
            bool(r.get('is_self')),
            bool(r.get('is_video')),
            clean_str(r.get('domain')),
            json.dumps(r.get('media')) if r.get('media') else None,
            json.dumps(r.get('preview')) if r.get('preview') else None,
            now,
            now
        ))
    async with pool.acquire() as conn:
        for i in range(0,len(vals),500):
            await conn.executemany(
                "INSERT INTO posts(post_id,title,selftext,author,created_utc,num_comments,score,upvote_ratio,url,permalink,subreddit,over_18,stickied,locked,is_self,is_video,domain,media,preview,last_updated_utc,last_checked_utc) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21) ON CONFLICT(post_id) DO UPDATE SET title=EXCLUDED.title,selftext=EXCLUDED.selftext,author=EXCLUDED.author,num_comments=EXCLUDED.num_comments,score=EXCLUDED.score,upvote_ratio=EXCLUDED.upvote_ratio,url=EXCLUDED.url,permalink=EXCLUDED.permalink,subreddit=EXCLUDED.subreddit,over_18=EXCLUDED.over_18,stickied=EXCLUDED.stickied,locked=EXCLUDED.locked,is_self=EXCLUDED.is_self,is_video=EXCLUDED.is_video,domain=EXCLUDED.domain,media=EXCLUDED.media,preview=EXCLUDED.preview,last_updated_utc=EXCLUDED.last_updated_utc,last_checked_utc=EXCLUDED.last_checked_utc",
                vals[i:i+500]
            )

async def batch_insert_comments(pool,records):
    now=time.time()
    vals=[]
    for r in records:
        vals.append((
            clean_str(r.get('id')),
            clean_str(r.get('post_id')),
            clean_str(r.get('author')),
            clean_str(r.get('body')),
            float(r.get('created_utc') or 0),
            int(r.get('score') or 0),
            clean_str(r.get('parent_id')),
            bool(r.get('is_submitter')),
            clean_str(r.get('permalink')),
            now
        ))
    async with pool.acquire() as conn:
        for i in range(0,len(vals),500):
            await conn.executemany(
                "INSERT INTO comments(comment_id,post_id,author,body,created_utc,score,parent_id,is_submitter,permalink,last_updated_utc) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT(comment_id) DO UPDATE SET score=EXCLUDED.score,last_updated_utc=EXCLUDED.last_updated_utc",
                vals[i:i+500]
            )

def stream_items(path):
    with open(path,encoding='utf-8',errors='replace') as f:
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)

async def import_posts(pool):
    batch=[]
    for post in stream_items(POSTS_FILE):
        batch.append(post)
        if len(batch)>=500:
            await batch_insert_posts(pool,batch)
            batch.clear()
    if batch:
        await batch_insert_posts(pool,batch)

async def import_comments(pool):
    batch=[]
    for comment in stream_items(COMMENTS_FILE):
        batch.append(comment)
        if len(batch)>=500:
            await batch_insert_comments(pool,batch)
            batch.clear()
    if batch:
        await batch_insert_comments(pool,batch)

async def main():
    pool=await asyncpg.create_pool(**DB_PARAMS)
    await create_tables(pool)
    await import_posts(pool)
    await import_comments(pool)
    await pool.close()

if __name__=='__main__':
    asyncio.run(main())

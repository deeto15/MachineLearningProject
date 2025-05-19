import asyncio
import asyncpg
from stock_market.formatter import date_formatter 
from scraper.helper_methods import DB_PARAMS

async def fetch_and_format_dates():
    """
    Connects to the database, fetches extracted_date and created_utc from comments,
    and applies date_formatter to each row.
    """
    conn = await asyncpg.connect(
        user=DB_PARAMS["user"],
        password=DB_PARAMS["password"],
        database=DB_PARAMS["database"],
        host=DB_PARAMS["host"],
        port=DB_PARAMS["port"],
    )
    rows = await conn.fetch("SELECT extracted_date, created_utc FROM test_comments")
    results = []
    for row in rows:
        extracted_date = row["extracted_date"]
        created_utc = row["created_utc"]
        formatted = date_formatter(created_utc, extracted_date)
        results.append((extracted_date, created_utc, formatted))
        print(f"Input: {extracted_date}, {created_utc} -> Output: {formatted}")
    await conn.close()
    return results

asyncio.run(fetch_and_format_dates())
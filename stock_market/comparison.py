import asyncio
from datetime import datetime, timezone
import os
import asyncpg
from stock_market.formatter import date_formatter
from scraper.helper_methods import DB_PARAMS
from tiingo import TiingoClient

async def fetch_and_format_dates():
    """
    Connects to the database, fetches extracted_date and created_utc from comments,
    and applies date_formatter to each row.
    """
    config = {}
    config['session'] = True
    config['api_key'] = os.environ["TIINGO_API_KEY"]
    client = TiingoClient(config)
    conn = await asyncpg.connect(
        user=DB_PARAMS["user"],
        password=DB_PARAMS["password"],
        database=DB_PARAMS["database"],
        host=DB_PARAMS["host"],
        port=DB_PARAMS["port"],
    )
    rows = await conn.fetch("SELECT extracted_date, extracted_stock, extracted_price, created_utc, body FROM test_comments")
    results = []
    for row in rows:
        extracted_date = row["extracted_date"]
        extracted_stock = row["extracted_stock"].upper()
        extracted_price = row["extracted_price"]
        created_utc = row["created_utc"]
        body = row["body"]
        original_date = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        original_date = original_date.strftime("%Y-%m-%d")
        formatted_date = date_formatter(created_utc, extracted_date)
        print(f"Original Date: {original_date}, Extracted Date: {formatted_date}, Time: {extracted_date}, Stock: {extracted_stock}, Price: {extracted_price}")
        
        results.append((extracted_date, created_utc, formatted_date))
        # try:
        #     data = client.get_dataframe(
        #         extracted_stock,
        #         startDate=original_date,
        #         endDate=formatted_date,
        #         frequency='daily'
        #     )
        # except Exception as e:
        #     print(f"Error fetching data for {extracted_stock}: {e}")
        #     continue
        #print(data["close"])
        
    await conn.close()
    return results

asyncio.run(fetch_and_format_dates())


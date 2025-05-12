import asyncio
from past_scraper import run_past_scraper
from live_scraper import run_live_scraper


def main():
    try:
        asyncio.run(run_live_scraper)
        asyncio.run(run_past_scraper)
    except Exception as e:
        print(f"Fatal error: {e}")

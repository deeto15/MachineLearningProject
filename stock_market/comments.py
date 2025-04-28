import asyncio
import csv
import json
import os

import pandas as pd

from .formatter import date_formatter, price_formatter


# get the newest comments from the hottest submission up to the comment limit
async def hottest_new_comments(reddit_client, comment_limit: int):
    subreddit = reddit_client.subreddit("wallstreetbets")
    hottest_submission_generator = subreddit.search(
        "What Are Your Moves Tomorrow", limit=1
    )
    hottest_submission = next(hottest_submission_generator, None)
    # hottest_submission = next(subreddit.hot(limit=1))
    print(hottest_submission.title)
    hottest_submission.comment_sort = "new"
    hottest_submission.comments.replace_more(limit=None)

    comments = hottest_submission.comments.list()[:comment_limit]
    return comments


comment_stock_info_prompt = """
Your task is to extract 3 specific stock-related variables from Reddit comments or titles. You will output a JSON object like this:

{
  "stockName": "",
  "userPosition": "",
  "priceDate": ""
}

Rules:
1. Extract only widely known stock names (e.g., AAPL, NVDA) or ETF's/Mutual Funds (e.g., VOO, IWM). Ignore meme abbreviations (e.g., WSB, NANA).
2. "stockName" must be one word or a 3-5 letter abbreviation.
3. "userPosition" is the price the user predicts.
4. "priceDate" is the date the user predicts.

Instructions:
- Always initialize JSON fields as empty unless explicitly populated.
- Do not fill out userPosition or priceDate or stockName unless all 3 are explicitly stated in the comment. 
- If you are presented with multiple options, pick the ones that you think are most relevant so that each field only has one value in it
Example Input: "I think AAPL will hit $150 in 3d. "
Example Output:
{
  "stockName": "AAPL",
  "userPosition": "$150",
  "priceDate": "3d"
}
"""


def get_gpt_parameters(comment_text: str) -> dict:
    return {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": comment_stock_info_prompt},
            {"role": "user", "content": comment_text},
        ],
    }


# use gpt to enumerate potential stock json information from the comment
async def get_comment_stock_info(gpt_client, comment):
    response = await asyncio.to_thread(
        gpt_client.chat.completions.create, **get_gpt_parameters(comment.body)
    )

    response_json = json.loads(response.choices[0].message.content)
    response_json["body"] = comment.body
    # response_json['time'] = comment.created_utc
    # response_json['header'] = comment.id
    # response_json['predictedDate'] = date_formatter(float(response_json['time']), response_json['priceDate'])
    # response_json['formattedPrice'] = price_formatter(response_json['userPosition'])

    return response_json


# return json results for scraped comments along with their gpt stock information
async def scrape_comments(reddit_client, gpt_client, comment_limit) -> list[dict]:
    comments = await hottest_new_comments(reddit_client, comment_limit)

    tasks = [get_comment_stock_info(gpt_client, comment) for comment in comments]
    results = await asyncio.gather(*tasks)

    return results


# organize the comment informatin by company ticker
def company_info_from_comments(comment_results: list[dict]):
    company_results = {}

    for comment in comment_results:
        ticker = comment.get("stockName", None)
        header = comment.get("header", None)
        user_position = comment.get("userPosition", None)
        formatted_price = comment.get("formattedPrice", None)
        price_date = comment.get("priceDate", None)
        expected_date = comment.get("predictedDate", None)
        body = comment.get("body", None)
        time = comment.get("time", None)
        # skip if there was no ticker
        if ticker == None:
            continue

        # append to the company's results if it's already in the dictionary
        if ticker in company_results:
            appendable_attributes = [
                "userPosition",
                "header",
                "priceDate",
                "predictedDate",
                "formattedPrice",
                "body",
                "time",
            ]

            for attr in appendable_attributes:
                comment_value = comment.get(attr, None)

                if comment_value != None and comment_value != "":
                    company_results[ticker][attr].append(comment_value)

            continue

        # new entry
        company_results[ticker] = {
            "userPosition": [user_position],
            "header": [header],
            "priceDate": [price_date],
            "predictedDate": [expected_date],
            "formattedPrice": [formatted_price],
            "body": [body],
            "time": [time],
        }

    return company_results


def write_comment_to_excel(company, details, excel_file="/app/data/comments.xlsx"):
    columns = ["header", "stockName", "formattedPrice", "predictedDate", "body", "time"]

    # Check if the Excel file exists
    if os.path.exists(excel_file):
        # Load existing data
        existing_data = pd.read_excel(excel_file, engine="openpyxl")
        existing_ids = set(existing_data["header"].astype(str))
    else:
        # If file doesn't exist, initialize an empty DataFrame
        existing_ids = set()

    # Extract comments from details
    new_comments = []
    for comment_id, formatted_price, predicted_date, body, time in zip(
        details["header"],
        details["formattedPrice"],
        details["predictedDate"],
        details["body"],
        details["time"],
    ):
        if not (company):
            continue
        # Check for duplicate comment IDs
        if str(comment_id) not in existing_ids:
            new_comments.append(
                {
                    "header": comment_id,
                    "stockName": company,
                    "formattedPrice": formatted_price,
                    "predictedDate": predicted_date,
                    "body": body,
                    "time": time,
                }
            )

    # If no new comments, exit early
    if not new_comments:
        return

    # Convert new comments to DataFrame
    new_data = pd.DataFrame(new_comments, columns=columns)

    # Append new comments to the file or create it
    if os.path.exists(excel_file):
        existing_data = pd.read_excel(excel_file, engine="openpyxl")
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)
    else:
        combined_data = new_data

    # Save to Excel
    combined_data.to_excel(excel_file, index=False, engine="openpyxl")

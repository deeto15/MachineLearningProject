import os

from praw import Reddit


def get_reddit_client() -> Reddit:
    reddit_client = Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
        password=os.getenv("REDDIT_PASSWORD"),
        username=os.getenv("REDDIT_USERNAME"),
        check_for_async=False,
    )
    return reddit_client

def hottest_new_comments(reddit_client, comment_limit: int):
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
    for comment in comments:
        print(comment)

client = get_reddit_client()
hottest_new_comments(client, 100)


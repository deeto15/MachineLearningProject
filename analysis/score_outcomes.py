# Scores predicted trades against real market data: for every comment the
# classifier flagged as a trade (prediction=1) whose expiry has passed, pulls
# daily prices via yfinance and records whether the call was right.
#
#   direction_correct - did the stock move the way the trade implied
#                       (calls -> up, puts -> down) between comment and expiry
#   strike_hit        - did the price touch the strike before expiry
#                       (calls: daily high >= strike, puts: daily low <= strike)
#   pct_move          - percent change from comment date close to expiry close
#
# Results land in an `outcomes` table in the same database, keyed by comment id,
# so Datasette can browse them and re-runs only score new comments.
#
# Run on the host (needs internet):
#   python analysis/score_outcomes.py            # score newly expired trades
#   python analysis/score_outcomes.py --rescore  # wipe and score everything again
import argparse
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "comments.db"

OUTCOMES_SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
    comment_id TEXT PRIMARY KEY REFERENCES comments (id),
    stock TEXT,
    option_type TEXT,
    strike REAL,
    expiry TEXT,
    comment_date TEXT,
    price_at_comment REAL,
    price_at_expiry REAL,
    pct_move REAL,
    direction_correct INTEGER,
    strike_hit INTEGER,
    scored_at TEXT DEFAULT (datetime('now'))
)
"""


def load_candidates(conn, rescore):
    """Trades with a known ticker, direction, and an expiry that has passed."""
    query = """
        SELECT c.id, c.stock, c.option_type, c.price, c.formatted_date, c.created_unix
        FROM comments c
        WHERE c.prediction = 1
          AND c.stock IS NOT NULL
          AND c.option_type IS NOT NULL
          AND c.formatted_date IS NOT NULL
          AND c.formatted_date != ''
          AND date(c.formatted_date) < date('now')
    """
    if not rescore:
        query += " AND c.id NOT IN (SELECT comment_id FROM outcomes)"
    return conn.execute(query).fetchall()


def fetch_history(ticker, start, end):
    try:
        hist = yf.Ticker(ticker).history(
            start=start.isoformat(), end=(end + timedelta(days=5)).isoformat(),
            auto_adjust=False,
        )
    except Exception as e:
        print(f"  {ticker}: download failed ({e})")
        return None
    if hist is None or hist.empty:
        return None
    hist.index = hist.index.tz_localize(None)
    return hist


def close_on_or_before(hist, day):
    """Close of the given date, or the nearest trading day before it."""
    rows = hist.loc[:pd.Timestamp(day)]
    if rows.empty:
        return None
    return float(rows["Close"].iloc[-1])


def score(conn, rescore):
    candidates = load_candidates(conn, rescore)
    print(f"{len(candidates)} expired trades to score")
    if not candidates:
        return

    # group by ticker so each symbol is downloaded once for its full date span
    by_ticker = {}
    for row in candidates:
        by_ticker.setdefault(row[1], []).append(row)

    scored, skipped = 0, 0
    for ticker, rows in sorted(by_ticker.items()):
        comment_days = [date.fromtimestamp(r[5]) for r in rows]
        expiries = [date.fromisoformat(r[4]) for r in rows]
        hist = fetch_history(ticker, min(comment_days) - timedelta(days=7), max(expiries))
        if hist is None:
            print(f"  {ticker}: no price data, skipping {len(rows)} trades")
            skipped += len(rows)
            continue

        for (comment_id, stock, option_type, price, expiry_str, created_unix) in rows:
            comment_day = date.fromtimestamp(created_unix)
            expiry = date.fromisoformat(expiry_str)
            p_start = close_on_or_before(hist, comment_day)
            p_end = close_on_or_before(hist, expiry)
            if p_start is None or p_end is None or p_start == 0:
                skipped += 1
                continue

            is_call = option_type.lower().startswith("c")
            pct_move = (p_end - p_start) / p_start * 100
            direction_correct = int(p_end > p_start) if is_call else int(p_end < p_start)

            strike, strike_hit = None, None
            try:
                strike = float(str(price).lstrip("$"))
            except (TypeError, ValueError):
                pass
            if strike is not None:
                window = hist.loc[pd.Timestamp(comment_day):pd.Timestamp(expiry)]
                if not window.empty:
                    if is_call:
                        strike_hit = int(float(window["High"].max()) >= strike)
                    else:
                        strike_hit = int(float(window["Low"].min()) <= strike)

            conn.execute(
                """INSERT OR REPLACE INTO outcomes
                   (comment_id, stock, option_type, strike, expiry, comment_date,
                    price_at_comment, price_at_expiry, pct_move, direction_correct, strike_hit)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (comment_id, stock, option_type, strike, expiry_str,
                 comment_day.isoformat(), round(p_start, 4), round(p_end, 4),
                 round(pct_move, 3), direction_correct, strike_hit),
            )
            scored += 1
        conn.commit()

    print(f"scored {scored}, skipped {skipped} (no price data)")


def summarize(conn):
    total, correct = conn.execute(
        "SELECT COUNT(*), SUM(direction_correct) FROM outcomes"
    ).fetchone()
    if not total:
        print("no outcomes yet - trades need to expire first")
        return
    print(f"\n=== outcomes so far ({total} scored trades) ===")
    print(f"direction correct: {correct}/{total} ({100 * correct / total:.1f}%)")
    hits = conn.execute(
        "SELECT COUNT(*), SUM(strike_hit) FROM outcomes WHERE strike_hit IS NOT NULL"
    ).fetchone()
    if hits[0]:
        print(f"strike hit:        {hits[1]}/{hits[0]} ({100 * hits[1] / hits[0]:.1f}%)")
    for opt, n, corr in conn.execute(
        """SELECT option_type, COUNT(*), SUM(direction_correct)
           FROM outcomes GROUP BY option_type ORDER BY COUNT(*) DESC"""
    ):
        print(f"  {opt:6s}: {corr}/{n} direction correct")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rescore", action="store_true", help="re-score all trades from scratch")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(OUTCOMES_SCHEMA)
    if args.rescore:
        conn.execute("DELETE FROM outcomes")
    conn.commit()
    score(conn, args.rescore)
    summarize(conn)
    conn.close()


if __name__ == "__main__":
    main()

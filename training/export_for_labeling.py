# Active-learning export: pulls the comments the classifier was LEAST confident
# about from the live database, prefilled with the model's guesses, so a human
# can correct them quickly. Corrected files feed back in via merge_labels.py.
#
#   python training/export_for_labeling.py               # 100 least-confident
#   python training/export_for_labeling.py --n 250
#
# Output: training/data/to_label.csv - open it, fix the Ticker/Strike/Expiry/
# OptionType/Label columns where the model got them wrong, delete rows you
# don't want, save, then run merge_labels.py.
import argparse
import csv
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "comments.db"
OUT = Path(__file__).resolve().parent / "data" / "to_label.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT id, body, stock, price, date, option_type, prediction, confidence
           FROM comments
           WHERE length(body) BETWEEN 10 AND 400
           ORDER BY confidence ASC
           LIMIT ?""",
        (args.n,),
    ).fetchall()
    conn.close()

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "confidence", "Comment", "Ticker", "Strike", "Expiry", "OptionType", "Label"])
        for (comment_id, body, stock, price, date, option_type, prediction, confidence) in rows:
            writer.writerow([
                comment_id, round(confidence or 0, 3), " ".join((body or "").split()),
                stock or "", price or "", date or "", option_type or "", prediction,
            ])
    print(f"wrote {len(rows)} least-confident comments to {OUT}")
    print("fix the entity/Label columns, then: python training/merge_labels.py")


if __name__ == "__main__":
    main()

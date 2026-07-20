# Merges a corrected to_label.csv (from export_for_labeling.py) into the main
# training CSV, skipping comments that are already in it. Run the training
# scripts afterwards to retrain on the enlarged set.
#
#   python training/merge_labels.py
import csv
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
LABELED = DATA_DIR / "to_label.csv"
TRAIN = DATA_DIR / "regression_model_training_data.csv"


def main():
    if not LABELED.exists():
        print(f"{LABELED} not found - run export_for_labeling.py and correct it first")
        return

    labeled = pd.read_csv(LABELED).fillna("")
    train = pd.read_csv(TRAIN)
    existing = set(train["Comment"].astype(str))

    added = 0
    with open(TRAIN, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for _, row in labeled.iterrows():
            comment = str(row["Comment"]).strip()
            if not comment or comment in existing:
                continue
            writer.writerow([
                comment, row["Ticker"], row["Strike"], row["Expiry"],
                row["OptionType"], "", "", int(row["Label"]),
            ])
            existing.add(comment)
            added += 1

    print(f"added {added} new labeled rows to {TRAIN.name} ({len(labeled) - added} skipped)")
    print("retrain with: python training/train_ner.py && python training/train_binary.py")
    LABELED.rename(LABELED.with_suffix(".merged.csv"))


if __name__ == "__main__":
    main()

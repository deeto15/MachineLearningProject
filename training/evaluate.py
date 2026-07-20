# Evaluates the live models against the hand-labeled REAL comment set
# (training/data/eval_real.csv) - the honest benchmark, unlike the training
# eval split which contains synthetic rows the models saw the templates of.
#
# Reports:
#   - classifier accuracy + macro F1 over the 3 classes
#   - field-level NER precision/recall/F1: the extracted Ticker/Strike/Expiry/
#     OptionType strings must match the labeled ones (case/$-insensitive)
#
# Usage:
#   python training/evaluate.py                      # evaluates the live models
#   python training/evaluate.py --ner <dir> --clf <dir>
import argparse
from pathlib import Path

import pandas as pd
import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoTokenizer,
)

ROOT = Path(__file__).resolve().parent.parent
EVAL_FILE = Path(__file__).resolve().parent / "data" / "eval_real.csv"
FIELDS = {"TICKER": "Ticker", "STRIKE": "Strike", "EXPIRY": "Expiry", "OPTIONTYPE": "OptionType"}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def normalize(value):
    return str(value).strip().lstrip("$").lower()


def extract_entities(model, tokenizer, id2label, text):
    enc = tokenizer(text, return_tensors="pt", truncation=True, return_offsets_mapping=True)
    offsets = enc.pop("offset_mapping")[0].tolist()
    with torch.no_grad():
        logits = model(**{k: v.to(device) for k, v in enc.items()}).logits[0]
    scores = torch.softmax(logits, -1).max(-1).values.tolist()
    preds = logits.argmax(-1).tolist()

    best = {}
    cur_label, cur_start, cur_end, cur_scores = None, None, None, []

    def close():
        if cur_label:
            span = text[cur_start:cur_end].strip()
            score = sum(cur_scores) / len(cur_scores)
            if cur_label not in best or score > best[cur_label][1]:
                best[cur_label] = (span, score)

    for (start, end), p, s in zip(offsets, preds, scores):
        if start == end:
            continue
        label = id2label[p]
        base = label.split("-", 1)[-1]
        if label.startswith("B-") or (label.startswith("I-") and base != cur_label):
            close()
            cur_label, cur_start, cur_end, cur_scores = base, start, end, [s]
        elif label.startswith("I-"):
            cur_end, cur_scores = end, cur_scores + [s]
        else:
            close()
            cur_label, cur_scores = None, []
    close()
    return {label: value for label, (value, _) in best.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ner", default=str(ROOT / "training_models" / "ner-V6-deberta"))
    parser.add_argument("--clf", default=str(ROOT / "training_models" / "classifier-V5-bert"))
    args = parser.parse_args()

    df = pd.read_csv(EVAL_FILE).fillna("")
    print(f"{len(df)} labeled real comments | NER: {Path(args.ner).name} | CLF: {Path(args.clf).name}")

    # --- classifier ---
    clf = AutoModelForSequenceClassification.from_pretrained(args.clf).to(device).eval()
    clf_tok = AutoTokenizer.from_pretrained(args.clf)
    preds = []
    for text in df["Comment"]:
        enc = clf_tok(text, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            logits = clf(**{k: v.to(device) for k, v in enc.items()}).logits[0]
        preds.append(int(logits.argmax()))
    del clf
    torch.cuda.empty_cache()

    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    gold = df["Label"].astype(int).tolist()
    print("\n=== classifier ===")
    print(f"accuracy: {accuracy_score(gold, preds):.3f}   macro F1: {f1_score(gold, preds, average='macro'):.3f}")
    print("confusion matrix (rows=gold 0/1/2, cols=predicted):")
    print(confusion_matrix(gold, preds, labels=[0, 1, 2]))

    # --- NER ---
    ner = AutoModelForTokenClassification.from_pretrained(args.ner).to(device).eval()
    ner_tok = AutoTokenizer.from_pretrained(args.ner)
    id2label = ner.config.id2label

    stats = {f: [0, 0, 0] for f in FIELDS}  # tp, fp, fn
    for _, row in df.iterrows():
        extracted = extract_entities(ner, ner_tok, id2label, row["Comment"])
        for tag, col in FIELDS.items():
            gold_val, pred_val = normalize(row[col]), normalize(extracted.get(tag, ""))
            if gold_val and pred_val:
                if gold_val == pred_val:
                    stats[tag][0] += 1
                else:
                    stats[tag][1] += 1
                    stats[tag][2] += 1
            elif pred_val:
                stats[tag][1] += 1
            elif gold_val:
                stats[tag][2] += 1

    print("\n=== NER (field-level, exact match after normalization) ===")
    total = [0, 0, 0]
    for tag, (tp, fp, fn) in stats.items():
        for i, v in enumerate((tp, fp, fn)):
            total[i] += v
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        print(f"{tag:10s}: P {p:.3f}  R {r:.3f}  F1 {f1:.3f}   (tp {tp} / fp {fp} / fn {fn})")
    tp, fp, fn = total
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    print(f"{'micro avg':10s}: P {p:.3f}  R {r:.3f}  F1 {f1:.3f}")


if __name__ == "__main__":
    main()

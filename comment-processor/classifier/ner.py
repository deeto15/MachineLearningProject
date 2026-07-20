# Runs the trained NER model on incoming comments and extracts trade entities
import os
import re

import torch
import torch.nn.functional
from transformers import AutoModelForTokenClassification, AutoTokenizer

import tickers
from classifier.binary import load_model
from dates import date_formatter

MODEL_PATH = os.getenv("NER_MODEL_PATH", "/models/ner-output-V5")
NER_VERSION = os.path.basename(MODEL_PATH.rstrip("/"))

# known ticker symbols + company-name lookup; extracted tickers that resolve to
# neither are discarded as false positives ("Space", "RAM"), while company
# names resolve to their symbol ("Sandisk" -> SNDK)
ticker_universe, ticker_names = tickers.load()

GLUED_STRIKE = re.compile(r"^\$?(\d+(?:\.\d+)?)([cp])$", re.IGNORECASE)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH).to(device)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
id2label = model.config.id2label
model.eval()

# maps NER labels to the field names used downstream
LABEL_TO_FIELD = {
    "TICKER": "Stock",
    "STRIKE": "Price",
    "EXPIRY": "Date",
    "OPTIONTYPE": "OptionType",
}


# Takes in comment bodies, tokenizes them, and returns the extracted entities per text
def tokens_batch(texts):
    encodings = tokenizer(
        texts,
        return_offsets_mapping=True,
        return_tensors="pt",
        truncation=True,
        padding=True,
    )
    offsets = encodings.pop("offset_mapping").tolist()
    input_ids = encodings["input_ids"]
    token_lists = [tokenizer.convert_ids_to_tokens(seq) for seq in input_ids]
    encodings = {k: v.to(device) for k, v in encodings.items()}
    with torch.no_grad():
        outputs = model(**encodings)
    logits = outputs.logits
    results = []
    for i in range(len(texts)):
        logit = logits[i]
        prediction = torch.argmax(logit, dim=-1).tolist()
        probs = torch.nn.functional.softmax(logit, dim=-1)
        scores = probs[range(len(prediction)), prediction]
        results.append(extractor(texts[i], offsets[i], token_lists[i], prediction, scores))
    return results


# Aligns subword tokens back to whole words so each full entity gets one label and
# confidence score, otherwise you'd output things like "January" as "Jan" "ua" "ry"
def extractor(text, offsets, token_list, predictions, scores):
    entities = []
    current_entity = []
    current_entity_offsets = []
    current_entity_scores = []
    current_label = None

    def close_entity():
        if current_entity:
            entity_score = sum(current_entity_scores) / len(current_entity_scores)
            entities.append(
                (current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score)
            )

    for token, pred_id, (start, end), score in zip(token_list, predictions, offsets, scores):
        # O tokens are anything that isn't part of a valid prediction
        label = id2label.get(pred_id, "O")
        if start == end:
            continue
        word = text[start:end]
        # B- tokens are the beginning of a whole entity, the "Jan" in the example above
        if label.startswith("B-"):
            close_entity()
            current_entity = [word]
            current_entity_scores = [score]
            current_entity_offsets = [(start, end)]
            current_label = label[2:]
        # I- tokens are the rest of the entity, the "ua" "ry"
        elif label.startswith("I-") and current_label == label[2:]:
            current_entity.append(word)
            current_entity_scores.append(score)
            current_entity_offsets.append((start, end))
        else:
            close_entity()
            current_entity = []
            current_entity_scores = []
            current_entity_offsets = []
            current_label = None

    close_entity()
    return entities


# Helper method to glue the tokens together correctly
def glue_tokens(text, pieces, offsets):
    if not pieces:
        return ""
    result = pieces[0]
    for i in range(1, len(pieces)):
        prev_end = offsets[i - 1][1]
        curr_start = offsets[i][0]
        if prev_end == curr_start:
            result += pieces[i]
        else:
            result += " " + pieces[i]
    # deberta-style tokenizers include the preceding space in token offsets
    return result.strip()


binary_version, binary_pipeline = load_model()


# Annotates each comment with the best-scoring extracted entities and the binary
# model's prediction, then returns the batch
def predict_comments(comments):
    bodies = [comment["body"] for comment in comments]
    entities_list = tokens_batch(bodies)
    for comment, entities in zip(comments, entities_list):
        best = {}
        for label, value, score in entities:
            if label in LABEL_TO_FIELD and (label not in best or score > best[label][1]):
                best[label] = (value, score)
        for label, (value, score) in best.items():
            field = LABEL_TO_FIELD[label]
            comment[field] = value
            comment[f"{field}Score"] = round(float(score), 4)
        # resolve extracted tickers: symbols pass through, company names map to
        # their symbol, anything else is dropped as a false positive
        if comment.get("Stock") and ticker_universe:
            symbol = tickers.resolve(comment["Stock"], ticker_universe, ticker_names)
            if symbol is None:
                comment.pop("Stock", None)
                comment.pop("StockScore", None)
            else:
                comment["Stock"] = symbol
        # split glued strikes like "450c" into price 450 + option type
        if comment.get("Price"):
            glued = GLUED_STRIKE.match(comment["Price"])
            if glued:
                comment["Price"] = glued.group(1)
                if not comment.get("OptionType"):
                    comment["OptionType"] = "calls" if glued.group(2).lower() == "c" else "puts"
                    comment["OptionTypeScore"] = comment.get("PriceScore")
            else:
                comment["Price"] = comment["Price"].lstrip("$")
        if comment.get("Date"):
            comment["FormattedDate"] = date_formatter(comment["created_unix"], comment["Date"])
        comment["NERModel"] = NER_VERSION

    preds, confs = binary_pipeline.predict_batch(bodies)
    for comment, pred, conf in zip(comments, preds, confs):
        comment["Prediction"] = int(pred)
        comment["Confidence"] = round(float(conf), 4)
        comment["BinaryModel"] = binary_version
    return comments

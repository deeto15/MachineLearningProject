# This generates predictions from the now trained model on new data
import json
import torch
import torch.nn.functional
from transformers import AutoModelForTokenClassification, AutoTokenizer
from stock_market.formatter import date_formatter
from Binary_Classifier.BERT_loader import load_model
import os

print(os.getcwd())
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_path = "./Binary_Classifier/training_models/ner-output-V4"
model = AutoModelForTokenClassification.from_pretrained(model_path).to(device)
tokenizer = AutoTokenizer.from_pretrained(model_path)
id2label = model.config.id2label
subset = {"TICKER", "PRICE", "DATE"}
model.eval()
def debug_tokens(text):
    enc = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        probs = model(**enc).logits.softmax(-1)[0]
    ids = probs.argmax(-1)
    toks = tokenizer.convert_ids_to_tokens(enc["input_ids"][0])
    return list(zip(toks, [id2label[i.item()] for i in ids], probs.max(-1).values.cpu().tolist()))


# Takes in comments, breaks it down into the tokenizer defined above and sends the text, its tokens and predictions to extractor
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
        result = extractor(
            texts[i],
            offsets[i],
            token_lists[i],
            prediction,
            scores,
        )
        results.append(result)
    return results



# Takes the tokens and aligns them to the predicted label, so that each full piece of the word has the confidence score and not invidual tokens, otherwise you'd output things like "January" as "Jan" "ua" "ry"
def extractor(text, offsets, token_list, predictions, scores):
    entities = []
    current_entity = []
    current_entity_offsets = []
    current_entity_scores = []
    current_label = None
    for token, pred_id, (start, end), score in zip(
        token_list, predictions, offsets, scores
    ):
        # O tokens are anything that isnt part of a valid prediction
        label = id2label.get(pred_id, "O")
        if start == end:
            continue
        word = text[start:end]
        # B tokens are the beginning of the whole token, the "Jan" in the individual example
        if label.startswith("B-"):
            if current_entity:
                entity_score = sum(current_entity_scores) / len(current_entity_scores)
                entities.append(
                    (
                        current_label,
                        glue_tokens(text, current_entity, current_entity_offsets),
                        entity_score,
                    )
                )
            current_entity = [word]
            current_entity_scores = [score]
            current_entity_offsets = [(start, end)]
            current_label = label[2:]
        # I- tokens are the rest of the original word, such as "ua" "ry"
        elif label.startswith("I-") and current_label == label[2:]:
            current_entity.append(word)
            current_entity_scores.append(score)
            current_entity_offsets.append((start, end))
        else:
            if current_entity:
                entity_score = sum(current_entity_scores) / len(current_entity_scores)
                entities.append(
                    (
                        current_label,
                        glue_tokens(text, current_entity, current_entity_offsets),
                        entity_score,
                    )
                )
            current_entity = []
            current_entity_scores = []
            current_entity_offsets = []
            current_label = None

    if current_entity:
        entity_score = sum(current_entity_scores) / len(current_entity_scores)
        entities.append(
            (
                current_label,
                glue_tokens(text, current_entity, current_entity_offsets),
                entity_score,
            )
        )

    best_entities = {}
    for label, value, score in entities:
        if label in subset:
            if label not in best_entities or score > best_entities[label][2]:
                best_entities[label] = (label, value, score)
    # Returns full tokens that are above the 80% confidence level
    if all(t in best_entities and best_entities[t][2] > 0.80 for t in subset):
        return {
            "Comment": text,
            "Stock": best_entities["TICKER"][1],
            "Price": best_entities["PRICE"][1],
            "Date": best_entities["DATE"][1],
            "StockScore": round(best_entities["TICKER"][2].item(), 4),
            "PriceScore": round(best_entities["PRICE"][2].item(), 4),
            "DateScore": round(best_entities["DATE"][2].item(), 4),
        }
    return None


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
    return result

def log_prediction_debug(text):
    encoding = tokenizer(
        text,
        return_offsets_mapping=True,
        return_tensors="pt",
        truncation=True,
    )
    offsets = encoding.pop("offset_mapping")[0].tolist()
    input_ids = encoding["input_ids"][0]
    token_list = tokenizer.convert_ids_to_tokens(input_ids)
    encoding = {k: v.to(device) for k, v in encoding.items()}
    with torch.no_grad():
        outputs = model(**encoding)
    logits = outputs.logits[0]
    predictions = torch.argmax(logits, dim=-1).tolist()
    probs = torch.nn.functional.softmax(logits, dim=-1)
    scores = probs[range(len(predictions)), predictions]
    for i, (tok, pred, score, (start, end)) in enumerate(zip(token_list, predictions, scores, offsets)):
        label = id2label.get(pred, "O")
        print(f"{tok:>10} | {label:>10} | {score:.4f} | {text[start:end]}")
    result = extractor(text, offsets, token_list, predictions, scores)
    print("EXTRACTED:", result)
    return result

version, pipeline = load_model()
def predict_comments(comments):
    bodies = [comment["body"] for comment in comments]
    entities_list = tokens_batch(bodies)
    dicts = []
    for comment, best_entities in zip(comments, entities_list):
        if not comment or not best_entities:
            continue
        comment["Stock"] = best_entities['Stock']
        comment["Price"] = best_entities['Price']
        comment["Date"] = best_entities['Date']
        comment["Formatted Date"] = date_formatter(comment["created_unix"], comment['Date'])
        comment["StockScore"] = best_entities['StockScore']
        comment["PriceScore"] = best_entities['PriceScore']
        comment["DateScore"] = best_entities['DateScore']
        comment["NER Version"] = model_path[-2:]
        dicts.append(comment)
    if dicts:
        good_comments = [comment["body"] for comment in dicts]
        preds, confs = pipeline.predict_batch(good_comments)
        for d, p, c in zip(dicts, preds, confs):
            d["Prediction"] = p
            d["Confidence"] = c
            d["Binary_Model"] = version[-2:]
        return dicts
    return []


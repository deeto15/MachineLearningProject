import csv
import json
from pathlib import Path
import torch.nn.functional
from transformers import AutoModelForTokenClassification, AutoTokenizer
import torch

output_csv = Path("regression_model_training_data.csv")
header = ["Comment", "Stock", "Price", "Date", "Label", "StockScore", "PriceScore", "DateScore"]
if not output_csv.exists():
    with open(output_csv, "w", newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(header)
# Load model and tokenizer
model_path = "./ner-output"
model = AutoModelForTokenClassification.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)
id2label = model.config.id2label
subset = {"TICKER", "PRICE", "DATE"}
model.eval()
file_path = Path.home() / "Downloads" / "wallstreetbets_submissions" / "wallstreetbets_submissions"
i = 0
# Helper to glue tokens while preserving original spacing
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

def extractor(text, offsets, tokens, predictions, scores, writer):
    entities = []
    current_entity = []
    current_entity_offsets = []
    current_entity_scores = []
    current_label = None

    for token, pred_id, (start, end), score in zip(tokens, predictions, offsets, scores):
        label = id2label.get(pred_id, "O")
        if start == end:
            continue
        word = text[start:end]

        if label.startswith("B-"):
            if current_entity:
                entity_score = sum(current_entity_scores) / len(current_entity_scores)
                entities.append((current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score))
            current_entity = [word]
            current_entity_scores = [score]
            current_entity_offsets = [(start, end)]
            current_label = label[2:]
        elif label.startswith("I-") and current_label == label[2:]:
            current_entity.append(word)
            current_entity_scores.append(score)
            current_entity_offsets.append((start, end))
        else:
            if current_entity:
                entity_score = sum(current_entity_scores) / len(current_entity_scores)
                entities.append((current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score))
            current_entity = []
            current_entity_offsets = []
            current_entity_scores = []
            current_label = None

    if current_entity:
        entity_score = sum(current_entity_scores) / len(current_entity_scores)
        entities.append((current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score))

    best_entities = {}
    for e in entities:
        entity_type = e[0]
        entity_score = e[2]
        if entity_type not in best_entities or entity_score > best_entities[entity_type][2]:
            best_entities[entity_type] = e

    if all(t in best_entities and best_entities[t][2] > 0.80 for t in subset):
        row = [
            text,
            best_entities["TICKER"][1],
            best_entities["PRICE"][1],
            best_entities["DATE"][1],
            1,
            round(best_entities["TICKER"][2].item(), 4),
            round(best_entities["PRICE"][2].item(), 4),
            round(best_entities["DATE"][2].item(), 4)
        ]
        writer.writerow(row)

    entities = []
    current_entity = []
    current_entity_offsets = []
    current_entity_scores = []
    current_label = None
    for token, pred_id, (start, end),score in zip(tokens, predictions, offsets, scores):
        label = id2label.get(pred_id, "O")

        if start == end:
            continue  # skip special tokens like [CLS], [SEP]

        word = text[start:end]

        if label.startswith("B-"):
            if current_entity:
                entity_score = sum(current_entity_scores) / len(current_entity_scores)
                entities.append((current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score))
            current_entity = [word]
            current_entity_scores = [score]
            current_entity_offsets = [(start, end)]
            current_label = label[2:]
        elif label.startswith("I-") and current_label == label[2:]:
            current_entity.append(word)
            current_entity_scores.append(score)
            current_entity_offsets.append((start, end))
        else:
            if current_entity:
                entity_score = sum(current_entity_scores) / len(current_entity_scores)
                entities.append((current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score))
            current_entity = []
            current_entity_offsets = []
            current_label = None
    
    if current_entity:
        entity_score = sum(current_entity_scores) / len(current_entity_scores)
        entities.append((current_label, glue_tokens(text, current_entity, current_entity_offsets), entity_score))
    best_entities = {}
    for e in entities:
        entity_type=e[0]
        entity_score=e[2]
        if entity_type not in best_entities or entity_score > best_entities[entity_type][2]:
            best_entities[entity_type] = e

    if all(t in best_entities and best_entities[t][2] > 0.80 for t in subset):
        global i
        print(text)
        print(i)
        i+=1
        for e in best_entities.values():
            print(f" {e[0]}: {e[1]}: {e[2]}")
            

def tokens(text, writer):
    encoding = tokenizer(text, return_offsets_mapping=True, return_tensors="pt", truncation=True)
    offsets = encoding.pop("offset_mapping")[0].tolist()
    input_ids = encoding["input_ids"][0]
    tokens = tokenizer.convert_ids_to_tokens(input_ids)

    with torch.no_grad():
        outputs = model(**encoding)
    logits = outputs.logits[0]
    predictions = torch.argmax(logits, dim=-1).tolist()
    probs = torch.nn.functional.softmax(logits, dim=-1)
    scores = probs[range(len(predictions)), predictions]
    extractor(text, offsets, tokens, predictions, scores, writer)

with open(output_csv, 'a', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    with open(file_path, 'r', encoding='utf-8') as f:
        for row in f:
            line = json.loads(row)
            tokens(line['title'], writer)
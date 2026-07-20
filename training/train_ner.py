# Trains the NER (token classification) model on the BIO-tagged data
import argparse
from pathlib import Path

import torch
from datasets import Dataset, DatasetDict
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

from bio_tagging import generate_labeled_data

DEFAULT_OUTPUT = str(Path(__file__).resolve().parent.parent / "training_models" / "ner-output-V5")

parser = argparse.ArgumentParser()
parser.add_argument(
    "--model",
    default="bert-base-uncased",
    help="base model to fine-tune, e.g. bert-base-uncased or microsoft/deberta-v3-base",
)
parser.add_argument("--output", default=DEFAULT_OUTPUT, help="directory to save the trained model")
args = parser.parse_args()
BASE_MODEL = args.model
OUTPUT_DIR = args.output
print(f"Fine-tuning {BASE_MODEL} -> {OUTPUT_DIR}")

label_list = [
    "O",
    "B-TICKER", "I-TICKER",
    "B-STRIKE", "I-STRIKE",
    "B-EXPIRY", "I-EXPIRY",
    "B-OPTIONTYPE", "I-OPTIONTYPE",
]
label2id = {label: i for i, label in enumerate(label_list)}
id2label = {i: label for label, i in label2id.items()}

data = generate_labeled_data()
print(f"Loaded {len(data)} training samples")
for d in data:
    d["ner_tags"] = [label2id[label] for label in d["ner_tags"]]

# hold out 10% so different base models can be compared on the same data
ds = Dataset.from_list(data).train_test_split(test_size=0.1, seed=42)
ds = DatasetDict({"train": ds["train"], "test": ds["test"]})
processing_class = AutoTokenizer.from_pretrained(BASE_MODEL)


# Tokenize the input tokens while preserving word boundaries
def tokenize_and_align_labels(example):
    tokenized_inputs = processing_class(
        example["tokens"],
        truncation=True,
        padding="max_length",
        max_length=128,
        is_split_into_words=True,
    )
    labels = []
    word_ids = tokenized_inputs.word_ids()
    prev_word_idx = None
    for word_idx in word_ids:
        # Special tokens like [CLS] etc
        if word_idx is None:
            labels.append(-100)
        # Start of a new word, use its original label
        elif word_idx != prev_word_idx:
            labels.append(example["ner_tags"][word_idx])
        # Continuation of the same word, switch to I- tag if not the first token in a word
        else:
            tag_id = example["ner_tags"][word_idx]
            tag = id2label[tag_id]
            if tag.startswith("B-"):
                labels.append(label2id[tag.replace("B-", "I-")])
            else:
                labels.append(tag_id)
        prev_word_idx = word_idx

    tokenized_inputs["labels"] = labels
    return tokenized_inputs


ds = ds.map(tokenize_and_align_labels, batched=False)
ds = ds.remove_columns(["tokens", "ner_tags"])

# dtype float32: some checkpoints (e.g. deberta-v3) are stored in fp16 and
# transformers loads them as-is; training raw fp16 NaNs out
model = AutoModelForTokenClassification.from_pretrained(
    BASE_MODEL,
    num_labels=len(label_list),
    id2label=id2label,
    label2id=label2id,
    dtype=torch.float32,
)
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    eval_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    remove_unused_columns=False,
)


# entity-level precision/recall/F1 on the held-out split
def compute_metrics(eval_pred):
    from seqeval.metrics import f1_score, precision_score, recall_score

    predictions, labels = eval_pred
    predictions = predictions.argmax(axis=-1)
    true_labels, true_preds = [], []
    for pred_seq, label_seq in zip(predictions, labels):
        labels_row, preds_row = [], []
        for p, l in zip(pred_seq, label_seq):
            if l != -100:
                labels_row.append(id2label[int(l)])
                preds_row.append(id2label[int(p)])
        true_labels.append(labels_row)
        true_preds.append(preds_row)
    return {
        "precision": precision_score(true_labels, true_preds),
        "recall": recall_score(true_labels, true_preds),
        "f1": f1_score(true_labels, true_preds),
    }


trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=ds["train"],
    eval_dataset=ds["test"],
    processing_class=processing_class,
    data_collator=DataCollatorForTokenClassification(processing_class),
    compute_metrics=compute_metrics,
)

trainer.train()
print("Final eval:", trainer.evaluate())
model.save_pretrained(OUTPUT_DIR)
processing_class.save_pretrained(OUTPUT_DIR)

# Trains the NER (token classification) model on the BIO-tagged data
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

OUTPUT_DIR = str(Path(__file__).resolve().parent.parent / "training_models" / "ner-output-V5")

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

ds = DatasetDict({"train": Dataset.from_list(data)})
processing_class = AutoTokenizer.from_pretrained("bert-base-uncased")


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

model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=len(label_list),
    id2label=id2label,
    label2id=label2id,
)
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    eval_strategy="no",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    no_cuda=not torch.cuda.is_available(),
    remove_unused_columns=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=ds["train"],
    processing_class=processing_class,
    data_collator=DataCollatorForTokenClassification(processing_class),
)

trainer.train()
model.save_pretrained(OUTPUT_DIR)
processing_class.save_pretrained(OUTPUT_DIR)

from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer
import os

def load_data(path):
    examples = []
    words = []
    labels = []

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                if words:
                    examples.append({"tokens": words, "ner_tags": labels})
                    words = []
                    labels = []
                continue
            token, label = line.split()
            words.append(token)
            labels.append(label)
    return examples

label_list = ['O', 'B-TICKER', 'I-TICKER', 'B-PRICE', 'I-PRICE', 'B-DATE', 'I-DATE']
label2id = {label: i for i, label in enumerate(label_list)}
id2label = {i: label for label, i in label2id.items()}

data = load_data("labeled_data.txt")
for d in data:
    d["ner_tags"] = [label2id[l] for l in d["ner_tags"]]

ds = Dataset.from_list(data)
ds = DatasetDict({"train": ds})

tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

def tokenize_and_align_labels(example):
    tokenized_inputs = tokenizer(
        example["tokens"],
        truncation=True,
        padding="max_length",   # ← this is key
        max_length=128,
        is_split_into_words=True
    )
    labels = []
    word_ids = tokenized_inputs.word_ids()
    prev_word_idx = None
    for word_idx in word_ids:
        if word_idx is None:
            labels.append(-100)
        elif word_idx != prev_word_idx:
            labels.append(example["ner_tags"][word_idx])
        else:
            labels.append(-100)
        prev_word_idx = word_idx
    tokenized_inputs["labels"] = labels
    return tokenized_inputs

ds = ds.map(tokenize_and_align_labels, batched=False)

from transformers import AutoModelForTokenClassification, TrainingArguments, Trainer

model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-cased",
    num_labels=len(label_list),
    id2label=id2label,
    label2id=label2id
)

training_args = TrainingArguments(
    output_dir="./ner-output",
    evaluation_strategy="no",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir="./logs",
)
from transformers import DataCollatorForTokenClassification

data_collator = DataCollatorForTokenClassification(tokenizer)
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=ds["train"],
    tokenizer=tokenizer,
    data_collator=data_collator
)

trainer.train()
model.save_pretrained('./ner-output')
tokenizer.save_pretrained('./ner-output')


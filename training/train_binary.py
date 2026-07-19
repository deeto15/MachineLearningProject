# Trains the sequence classification model that scores whole comments
from pathlib import Path

import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    BertForSequenceClassification,
    BertTokenizer,
    Trainer,
    TrainingArguments,
)

DATA_FILE = Path(__file__).resolve().parent / "data" / "regression_model_training_data.csv"
OUTPUT_DIR = str(Path(__file__).resolve().parent.parent / "training_models" / "classifier-bert-V4")

df = pd.read_csv(DATA_FILE)
df = df[["Comment", "Label"]].dropna()
df["labels"] = df["Label"].astype(int)
df = df.drop(columns=["Label"])
dataset = Dataset.from_pandas(df)

processing_class = BertTokenizer.from_pretrained("bert-base-uncased")


def tokenize(batch):
    return processing_class(
        batch["Comment"], truncation=True, padding="max_length", max_length=256
    )


dataset = dataset.map(tokenize, batched=True)
dataset = dataset.train_test_split(test_size=0.1)
dataset = dataset.remove_columns(["Comment"])

model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=3)
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    eval_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    no_cuda=not torch.cuda.is_available(),
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    processing_class=processing_class,
)

trainer.train()
model.save_pretrained(OUTPUT_DIR)
processing_class.save_pretrained(OUTPUT_DIR)

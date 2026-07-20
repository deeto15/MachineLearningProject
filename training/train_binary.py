# Trains the sequence classification model that scores whole comments
import argparse
from pathlib import Path

import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

DATA_FILE = Path(__file__).resolve().parent / "data" / "regression_model_training_data.csv"
SYNTHETIC_FILE = Path(__file__).resolve().parent / "data" / "synthetic_training_data.csv"
OUTPUT_DIR = str(Path(__file__).resolve().parent.parent / "training_models" / "classifier-bert-V4")

parser = argparse.ArgumentParser()
parser.add_argument(
    "--model",
    default="bert-base-uncased",
    help="base model to fine-tune, e.g. bert-base-uncased, microsoft/deberta-v3-base, or ProsusAI/finbert",
)
parser.add_argument("--output", default=OUTPUT_DIR, help="directory to save the trained model")
args = parser.parse_args()
BASE_MODEL = args.model
OUTPUT_DIR = args.output
print(f"Fine-tuning {BASE_MODEL} -> {OUTPUT_DIR}")

df = pd.read_csv(DATA_FILE)
if SYNTHETIC_FILE.exists():
    synthetic = pd.read_csv(SYNTHETIC_FILE)
    print(f"Including {len(synthetic)} synthetic samples from {SYNTHETIC_FILE.name}")
    df = pd.concat([df, synthetic], ignore_index=True)
df = df[["Comment", "Label"]].dropna()
df["labels"] = df["Label"].astype(int)
df = df.drop(columns=["Label"])
dataset = Dataset.from_pandas(df)

processing_class = AutoTokenizer.from_pretrained(BASE_MODEL)


def tokenize(batch):
    return processing_class(
        batch["Comment"], truncation=True, padding="max_length", max_length=256
    )


dataset = dataset.map(tokenize, batched=True)
# fixed seed so different base models are compared on the same held-out split
dataset = dataset.train_test_split(test_size=0.1, seed=42)
dataset = dataset.remove_columns(["Comment"])

# dtype float32: some checkpoints are stored in fp16 and load as-is; training
# raw fp16 NaNs out
model = AutoModelForSequenceClassification.from_pretrained(
    BASE_MODEL, num_labels=3, ignore_mismatched_sizes=True, dtype=torch.float32
)
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    eval_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
)

def compute_metrics(eval_pred):
    from sklearn.metrics import accuracy_score, f1_score

    logits, labels = eval_pred
    preds = logits.argmax(axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
    }


# class-weighted loss: label 2 (price targets) is rare and otherwise gets
# absorbed into the majority class
counts = torch.tensor(
    [max(1, int((df["labels"] == i).sum())) for i in range(3)], dtype=torch.float
)
class_weights = (counts.sum() / (3 * counts))
print(f"class counts: {counts.tolist()}  ->  loss weights: {[round(w, 3) for w in class_weights.tolist()]}")


class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss_fct = torch.nn.CrossEntropyLoss(weight=class_weights.to(outputs.logits.device))
        loss = loss_fct(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


trainer = WeightedTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    processing_class=processing_class,
    compute_metrics=compute_metrics,
)

trainer.train()
print("Final eval:", trainer.evaluate())
model.save_pretrained(OUTPUT_DIR)
processing_class.save_pretrained(OUTPUT_DIR)

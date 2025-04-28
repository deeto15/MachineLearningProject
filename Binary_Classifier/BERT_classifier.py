import pandas as pd
from datasets import Dataset
from transformers import (
    BertForSequenceClassification,
    BertTokenizer,
    Trainer,
    TrainingArguments,
)

df = pd.read_csv("NER_Classifier/regression_model_training_data.csv")
df = df[["Comment", "Label"]].dropna()
df["labels"] = df["Label"].astype(int)
df = df.drop(columns=["Label"])
dataset = Dataset.from_pandas(df)

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")


def tokenize(batch):
    return tokenizer(
        batch["Comment"], truncation=True, padding="max_length", max_length=256
    )


dataset = dataset.map(tokenize, batched=True)
dataset = dataset.train_test_split(test_size=0.1)
dataset = dataset.remove_columns(["Comment"])

model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=2)

training_args = TrainingArguments(
    output_dir="./training_models/classifier-bert-V2",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    tokenizer=tokenizer,
)

trainer.train()
model.save_pretrained("./training_models/classifier-bert-V2")
tokenizer.save_pretrained("./training_models/classifier-bert-V2")

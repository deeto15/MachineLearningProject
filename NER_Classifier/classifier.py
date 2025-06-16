# This is the actual model training on the now tokenized data
from sklearn.model_selection import train_test_split
from bio_tagging import generate_labeled_data
from datasets import Dataset, DatasetDict
import torch
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

label_list = ["O", "B-TICKER", "I-TICKER", "B-STRIKE", "I-STRIKE", "B-EXPIRY", "I-EXPIRY", "B-OPTIONTYPE", "I-OPTIONTYPE"]
label2id = {label: i for i, label in enumerate(label_list)}
id2label = {i: label for label, i in label2id.items()}

# Get tokenized data from the biotagger
data = generate_labeled_data()
print(f"Loaded {len(data)} training samples")
for d in data:
    d["ner_tags"] = [label2id[l] for l in d["ner_tags"]]

train_data, val_data = train_test_split(data, test_size=0.1, random_state=42)
# ds = DatasetDict({
#     "train": Dataset.from_list(train_data),
#     "validation": Dataset.from_list(val_data),
# })

ds = Dataset.from_list(data)
ds = DatasetDict({"train": ds})
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")


# Tokenize the input tokens while preserving word boundaries
def tokenize_and_align_labels(example):
    tokenized_inputs = tokenizer(
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
        # Continuation of the same word, switch to I tag if not the first token in a word
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

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=len(label_list),
    id2label=id2label,
    label2id=label2id,
)
training_args = TrainingArguments(
    output_dir="./training_models/ner-output-V5",
    eval_strategy="no",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    no_cuda=False,
    remove_unused_columns=False,
)
data_collator = DataCollatorForTokenClassification(tokenizer)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=ds["train"],
    #eval_dataset=ds["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
)

trainer.train()
model.save_pretrained("./training_models/ner-output-V5")
tokenizer.save_pretrained("./training_models/ner-output-V5")

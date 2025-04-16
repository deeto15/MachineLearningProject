#This is the actual model training on the now tokenized data
from datasets import Dataset, DatasetDict
from post_processing.bio_tagging import generate_labeled_data
from transformers import AutoModelForTokenClassification, TrainingArguments, Trainer, DataCollatorForTokenClassification, AutoTokenizer

label_list = ['O', 'B-TICKER', 'I-TICKER', 'B-PRICE', 'I-PRICE', 'B-DATE', 'I-DATE']
label2id = {label: i for i, label in enumerate(label_list)}
id2label = {i: label for label, i in label2id.items()}

#Get tokenized data from the biotagger
data = generate_labeled_data()
for d in data:
    d["ner_tags"] = [label2id[l] for l in d["ner_tags"]]

ds = Dataset.from_list(data)
ds = DatasetDict({"train": ds})
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

#Tokenize the input tokens while preserving word boundaries
def tokenize_and_align_labels(example):
    tokenized_inputs = tokenizer(
        example["tokens"],
        truncation=True,
        padding="max_length",
        max_length=128,
        is_split_into_words=True
    )
    labels = []
    word_ids = tokenized_inputs.word_ids()
    prev_word_idx = None
    for word_idx in word_ids:
        #Special tokens like [CLS] etc
        if word_idx is None:
            labels.append(-100)
        #Start of a new word, use its original label
        elif word_idx != prev_word_idx:
            labels.append(example["ner_tags"][word_idx])
        #Continuation of the same word, switch to I tag if not the first token in a word
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


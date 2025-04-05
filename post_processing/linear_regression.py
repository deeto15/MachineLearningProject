from transformers import AutoTokenizer, AutoModelForTokenClassification, TokenClassificationPipeline
import torch, json
#Bugs until the model is done (ideally)
#TODO Remove hardcoded filepath
#TODO add post processing to only take one a peice from each batch, and fitler out duplicates
#TODO ask Sam to optimize
#TODO add logistic regression layer
model_path = "./ner-output"
file_path = r"C:\Users\Kendall Eberly\Downloads\wallstreetbets_comments\wallstreetbets_comments.txt"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForTokenClassification.from_pretrained(model_path)
device = 0 if torch.cuda.is_available() else -1

ner_pipeline = TokenClassificationPipeline(
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
    device=device
)

def process_file_in_batches(file_path, batch_size=32):
    with open(file_path, "r", encoding="utf-8") as f:
        batch = []
        for line in f:
            try:
                data = json.loads(line)
                comment = data.get("body", "").strip()
                if not comment:
                    continue
                batch.append(comment)
                if len(batch) == batch_size:
                    results = ner_pipeline(batch)
                    yield batch, results
                    batch = []
            except json.JSONDecodeError:
                continue
        if batch:
            results = ner_pipeline(batch)
            yield batch, results


required_entities = {"TICKER", "PRICE", "DATE"}
threshold = 0.80

for comments, batch_results in process_file_in_batches(file_path, batch_size=32):
    for comment, entities in zip(comments, batch_results):
        found = {e['entity_group'] for e in entities if e['score'] > threshold}
        if required_entities.issubset(found):
            print(f"\nComment: {comment}")
            for entity in entities:
                if entity['score'] > threshold:
                    print(f"  {entity['entity_group']}: {entity['word']} (score={entity['score']:.2f})")



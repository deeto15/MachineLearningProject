from transformers import AutoTokenizer, AutoModelForTokenClassification, TokenClassificationPipeline

# Path to your trained model + tokenizer folder
model_path = "./ner-output"

# Load tokenizer and model directly from disk
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForTokenClassification.from_pretrained(model_path)

# Create the NER pipeline
ner_pipeline = TokenClassificationPipeline(
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple"
)

# Text to test
text = "GME to $200 by Mar 3rd"

# Run the pipeline
results = ner_pipeline(text)

# Output detected entities
print(f"\nInput: {text}")
print("Detected entities:")
for entity in results:
    print(f"  {entity['entity_group']}: {entity['word']} (score={entity['score']:.2f})")


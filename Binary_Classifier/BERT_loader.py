import torch
import torch.nn.functional as F
from transformers import BertForSequenceClassification, BertTokenizer


class BertIntentClassifier:
    def __init__(self, model_path="./training_models/classifier-bert-V2"):
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.model = BertForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

    def predict(self, text, threshold=0.43):
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=256, padding=True
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)[0]
        confidence = probs[1].item()
        prediction = int(confidence >= threshold)
        return prediction, confidence


def load_model(model_path="./training_models/classifier-bert-V2"):
    return BertIntentClassifier(model_path)

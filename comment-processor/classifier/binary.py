import os

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_PATH = os.getenv("BINARY_MODEL_PATH", "/models/classifier-bert-V4")


class BertIntentClassifier:
    def __init__(self, model_path=MODEL_PATH):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path).to(self.device)
        # fp16 only works reliably on GPU
        if self.device.type == "cuda":
            model = model.half()
            torch.backends.cudnn.benchmark = True
        self.model = model.eval()

    def predict_batch(self, texts, batch_size=32):
        preds, confs = [], []
        for i in range(0, len(texts), batch_size):
            inputs = self.tokenizer(
                texts[i : i + batch_size],
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=256,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)
            preds += torch.argmax(probs, dim=1).cpu().tolist()
            confs += probs.max(dim=1).values.cpu().tolist()
        return preds, confs


def load_model(model_path=MODEL_PATH):
    return os.path.basename(model_path.rstrip("/")), BertIntentClassifier(model_path)

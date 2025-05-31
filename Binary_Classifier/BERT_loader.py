import torch
from torch.amp import autocast
import torch.nn.functional as F
from transformers import BertTokenizer, BertForSequenceClassification


class BertIntentClassifier:
    def __init__(self, model_path="./training_models/classifier-bert-V3"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.model = (
            BertForSequenceClassification.from_pretrained(model_path)
            .to(self.device)
            .half()
        )
        self.model.eval()
        torch.backends.cudnn.benchmark = True

    def predict_batch(self, texts, threshold=0.43, batch_size=32):
        preds, confs = [], []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=256,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad(), autocast("cuda"):
                outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)
            conf_batch = probs[:, 1]
            pred_batch = (conf_batch >= threshold).long()
            preds += pred_batch.cpu().tolist()
            confs += conf_batch.cpu().tolist()
        return preds, confs


def load_model(model_path="./training_models/classifier-bert-V3"):
    return model_path, BertIntentClassifier(model_path)

"""bge-m3 (dense + sparse) va bge-reranker-v2-m3 ni transformers orqali ishlatish.

bge-m3: dense = oxirgi qatlam CLS vektori (L2 normallashtirilgan, 1024);
sparse = relu(sparse_linear(hidden)) har bir token uchun, bir xil token id lar bo'yicha maksimum,
maxsus tokenlar (CLS, EOS, PAD, UNK) chiqarib tashlanadi. Bu FlagEmbedding dagi BGEM3 bilan bir xil.
"""
import threading
from functools import lru_cache
from pathlib import Path

import torch
from django.conf import settings
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

_lock = threading.Lock()


def _device() -> str:
    if settings.EMBEDDING_DEVICE:
        return settings.EMBEDDING_DEVICE
    return "cuda" if torch.cuda.is_available() else "cpu"


class BGEM3:
    def __init__(self, path: str, device: str):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        self.model = AutoModel.from_pretrained(path, dtype=dtype).to(device).eval()
        self.sparse_linear = torch.nn.Linear(self.model.config.hidden_size, 1)
        self.sparse_linear.load_state_dict(torch.load(Path(path) / "sparse_linear.pt", map_location="cpu"))
        self.sparse_linear = self.sparse_linear.to(device=device, dtype=dtype).eval()
        self.special_ids = {self.tokenizer.cls_token_id, self.tokenizer.eos_token_id,
                            self.tokenizer.pad_token_id, self.tokenizer.unk_token_id}

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"])

    @torch.inference_mode()
    def encode(self, texts: list[str], batch_size: int = 16, max_length: int = 1024) -> list[tuple[list[float], dict[int, float]]]:
        """[(dense, {token_id: weight})] — kirish tartibida."""
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]), reverse=True)
        out: list = [None] * len(texts)
        for start in range(0, len(order), batch_size):
            idx = order[start:start + batch_size]
            batch = self.tokenizer([texts[i] for i in idx], padding=True, truncation=True,
                                   max_length=max_length, return_tensors="pt").to(self.device)
            hidden = self.model(**batch).last_hidden_state
            dense = torch.nn.functional.normalize(hidden[:, 0].float(), dim=-1).cpu().tolist()
            weights = torch.relu(self.sparse_linear(hidden)).squeeze(-1).float().cpu()
            ids = batch["input_ids"].cpu()
            for row, i in enumerate(idx):
                sparse: dict[int, float] = {}
                for tok, w in zip(ids[row].tolist(), weights[row].tolist()):
                    if w > 0 and tok not in self.special_ids and w > sparse.get(tok, 0.0):
                        sparse[tok] = w
                out[i] = (dense[row], sparse)
        return out


class Reranker:
    def __init__(self, path: str, device: str):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        self.model = AutoModelForSequenceClassification.from_pretrained(path, dtype=dtype).to(device).eval()

    @torch.inference_mode()
    def score(self, query: str, passages: list[str], batch_size: int = 16, max_length: int = 1024) -> list[float]:
        """0..1 oralig'idagi moslik bahosi (sigmoid)."""
        scores: list[float] = []
        for start in range(0, len(passages), batch_size):
            chunk = passages[start:start + batch_size]
            batch = self.tokenizer([query] * len(chunk), chunk, padding=True, truncation=True,
                                   max_length=max_length, return_tensors="pt").to(self.device)
            logits = self.model(**batch).logits.view(-1).float()
            scores.extend(torch.sigmoid(logits).cpu().tolist())
        return scores


@lru_cache(maxsize=1)
def get_embedder() -> BGEM3:
    with _lock:
        return BGEM3(settings.EMBEDDING_MODEL_PATH, _device())


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    with _lock:
        return Reranker(settings.RERANKER_MODEL_PATH, _device())

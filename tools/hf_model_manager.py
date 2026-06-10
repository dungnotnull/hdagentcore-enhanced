"""hf_model_manager.py — HuggingFace model manager for agentcore-enhanced."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Optional

MODELS_DIR = Path(__file__).parent.parent / "models"
IDLE_UNLOAD_SECONDS = 600

MODEL_REGISTRY = {
    "bge_large": {
        "model_id": "BAAI/bge-large-en-v1.5",
        "type": "sentence_transformer",
        "task": "text_embedding",
        "description": "MTEB #1 English embedding model; used for pattern semantic search",
    },
    "minilm": {
        "model_id": "sentence-transformers/all-MiniLM-L6-v2",
        "type": "sentence_transformer",
        "task": "text_embedding",
        "description": "Fast embedding for real-time benchmark clustering; 5x faster than BGE-large",
    },
    "codet5p": {
        "model_id": "Salesforce/codet5p-770m",
        "type": "seq2seq",
        "task": "code_analysis",
        "description": "Code pattern analysis and code->spec reverse engineering",
    },
    "bge_reranker": {
        "model_id": "BAAI/bge-reranker-large",
        "type": "cross_encoder",
        "task": "reranking",
        "description": "Cross-encoder reranker; post-retrieval relevance scoring for patterns",
    },
}


class HFModelManager:
    """Singleton lazy-loading HuggingFace model manager."""

    _instance: Optional["HFModelManager"] = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "HFModelManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = HFModelManager()
        return cls._instance

    def __init__(self):
        self._models: dict[str, Any] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._model_lock = threading.Lock()
        self._device = self._detect_device()
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

    def _detect_device(self) -> str:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _load_model(self, key: str) -> Any:
        cfg = MODEL_REGISTRY.get(key)
        if cfg is None:
            raise ValueError(f"Model key '{key}' not in registry")

        model_id = cfg["model_id"]
        model_type = cfg["type"]

        if model_type == "sentence_transformer":
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_id, cache_folder=str(MODELS_DIR))
            if self._device == "cuda":
                model = model.to("cuda")
            return model

        elif model_type == "cross_encoder":
            from sentence_transformers import CrossEncoder
            return CrossEncoder(model_id, max_length=512, device=self._device)

        elif model_type == "seq2seq":
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=str(MODELS_DIR))
            model = AutoModelForSeq2SeqLM.from_pretrained(model_id, cache_dir=str(MODELS_DIR))
            return {"tokenizer": tokenizer, "model": model}

        raise ValueError(f"Unknown model type: {model_type}")

    def _get_model(self, key: str) -> Any:
        with self._model_lock:
            if key not in self._models:
                self._models[key] = self._load_model(key)
            self._reset_idle_timer(key)
            return self._models[key]

    def _reset_idle_timer(self, key: str):
        if key in self._timers:
            self._timers[key].cancel()
        timer = threading.Timer(IDLE_UNLOAD_SECONDS, self._unload_model, args=[key])
        timer.daemon = True
        timer.start()
        self._timers[key] = timer

    def _unload_model(self, key: str):
        with self._model_lock:
            self._models.pop(key, None)

    def encode(self, texts: list[str], model_key: str = "bge_large") -> list[list[float]]:
        try:
            model = self._get_model(model_key)
            embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return embeddings.tolist()
        except Exception:
            return self._tfidf_fallback(texts)

    def encode_batch(self, texts: list[str], batch_size: int = 32, model_key: str = "bge_large") -> list[list[float]]:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self.encode(batch, model_key=model_key))
        return results

    def rerank(self, query: str, candidates: list[str], model_key: str = "bge_reranker") -> list[float]:
        try:
            model = self._get_model(model_key)
            pairs = [[query, c] for c in candidates]
            scores = model.predict(pairs, show_progress_bar=False)
            return scores.tolist() if hasattr(scores, "tolist") else list(scores)
        except Exception:
            return self._heuristic_rerank(query, candidates)

    def analyze_code(self, code_snippet: str, task: str = "summarize", model_key: str = "codet5p") -> str:
        try:
            components = self._get_model(model_key)
            tokenizer = components["tokenizer"]
            model = components["model"]
            inputs = tokenizer(code_snippet[:512], return_tensors="pt", max_length=512, truncation=True)
            outputs = model.generate(**inputs, max_new_tokens=128)
            return tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception:
            lines = code_snippet.strip().split("\n")
            return f"Code snippet ({len(lines)} lines)"

    def preload(self, keys: list[str]):
        for key in keys:
            try:
                self._get_model(key)
            except Exception:
                pass

    @staticmethod
    def _tfidf_fallback(texts: list[str]) -> list[list[float]]:
        import hashlib
        results = []
        dim = 64
        for text in texts:
            vec = [0.0] * dim
            for i, word in enumerate(text.lower().split()[:dim]):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                vec[h % dim] += 1.0
            norm = (sum(v * v for v in vec) ** 0.5) or 1.0
            results.append([v / norm for v in vec])
        return results

    @staticmethod
    def _heuristic_rerank(query: str, candidates: list[str]) -> list[float]:
        q_words = set(query.lower().split())
        scores = []
        for c in candidates:
            c_words = set(c.lower().split())
            overlap = len(q_words & c_words) / max(len(q_words), 1)
            scores.append(overlap)
        return scores

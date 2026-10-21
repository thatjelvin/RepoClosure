"""Lexical (BM25), semantic (embedding) and path-based retrievers.

Tokenization (documented for reproducibility): text is lower-cased; identifiers are
split on ``_`` and camelCase boundaries; tokens are ``[a-z0-9]+`` runs of length >= 2;
a small English stop-word list is removed. The same tokenizer is used by all lexical
variants so comparisons are fair.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .config import RetrievalConfig
from .parsing import Entity

_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "be",
    "with", "as", "by", "at", "it", "this", "that", "from", "not", "but", "if", "we",
    "you", "i", "he", "she", "they", "will", "can", "should", "would", "could", "do",
    "does", "did", "has", "have", "had", "was", "were", "self", "def", "return", "none",
    "true", "false", "import", "class", "try", "except", "raise", "pass", "lambda",
}

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        for piece in raw.split("_"):
            for sub in _CAMEL_RE.split(piece):
                low = sub.lower()
                if len(low) >= 2 and low not in _STOP and not low.isdigit():
                    out.append(low)
    return out


# --------------------------------------------------------------------------- #
# Lexical
# --------------------------------------------------------------------------- #
class BM25Retriever:
    """Okapi BM25 over entity documents (Robertson & Zaragoza, 2009)."""

    def __init__(self, config: RetrievalConfig | None = None):
        self.config = config or RetrievalConfig()
        self._ids: list[str] = []
        self._bm25 = None

    def fit(self, entities: Iterable[Entity]) -> "BM25Retriever":
        from rank_bm25 import BM25Okapi  # local import keeps the core import-light

        docs: list[list[str]] = []
        for ent in entities:
            self._ids.append(ent.id)
            docs.append(tokenize(ent.search_text(self.config.embed_max_chars)))
        if not docs:
            self._bm25 = None
            return self
        self._bm25 = BM25Okapi(docs, k1=self.config.bm25_k1, b=self.config.bm25_b)
        return self

    def score(self, query: str) -> dict[str, float]:
        if self._bm25 is None:
            return {doc_id: 0.0 for doc_id in self._ids}
        scores = self._bm25.get_scores(tokenize(query))
        return {doc_id: float(s) for doc_id, s in zip(self._ids, scores)}


# --------------------------------------------------------------------------- #
# Semantic
# --------------------------------------------------------------------------- #
_MODEL_CACHE: dict[str, object] = {}


class DenseRetriever:
    """Cosine-similarity dense retrieval with a small local embedding model.

    Prefers ``sentence-transformers``; falls back to a ``transformers`` mean-pooling
    encoder so the package still works with a minimal dependency set. Either way the
    model is local and needs no API key.
    """

    def __init__(self, config: RetrievalConfig | None = None):
        self.config = config or RetrievalConfig()
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None
        self._model = None
        self._backend = ""
        self._cache: dict[str, np.ndarray] = {}

    def _cache_tag(self) -> str:
        """Identity of the encoder, used to namespace cache keys.

        Without this, vectors produced by different backends/models would collide
        (e.g. the 256-dim hashing fallback vs. 384-dim MiniLM) and corrupt the cache.
        """
        return f"{self._backend}|{self.config.embed_model}|{self.config.embed_seq_length}"

    def set_cache(self, cache: dict[str, np.ndarray] | None) -> None:
        self._cache = dict(cache) if cache else {}

    def get_cache(self) -> dict[str, np.ndarray]:
        return self._cache

    def _load(self):
        if self._model is not None:
            return
        if self.config.embed_model == "hashing":
            # Dependency-free deterministic bag-of-tokens encoder. Documented as a
            # CPU-only / offline fallback and used for smoke tests. NOT the model used
            # for any reported experimental result.
            self._backend = "hashing"
            self._model = "hashing"
            return
        try:
            from sentence_transformers import SentenceTransformer
            import os

            import torch
            torch.set_num_threads(max(1, min(4, os.cpu_count() or 2)))
            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                pass  # already initialised
            cached = _MODEL_CACHE.get(self.config.embed_model)
            if cached is None:
                cached = SentenceTransformer(self.config.embed_model)
                cached.max_seq_length = self.config.embed_seq_length
                _MODEL_CACHE[self.config.embed_model] = cached
            self._model = cached
            self._backend = "sentence_transformers"
            return
        except Exception:  # pragma: no cover - fallback path
            pass
        from transformers import AutoModel, AutoTokenizer  # type: ignore
        self._tok = AutoTokenizer.from_pretrained(self.config.embed_model)
        self._model = AutoModel.from_pretrained(self.config.embed_model)
        self._backend = "transformers_meanpool"

    @staticmethod
    def _normalise(mat: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms

    def encode(self, texts: list[str]) -> np.ndarray:
        self._load()
        texts = [t[: self.config.embed_max_chars] for t in texts]
        keys = [f"{self._cache_tag()}:{hashlib.sha256(t.encode('utf-8', 'replace')).hexdigest()}"
                for t in texts]
        missing = [(i, t) for i, (k, t) in enumerate(zip(keys, texts)) if k not in self._cache]
        if missing:
            emb_new = self._encode_uncached([t for _, t in missing])
            for (idx, _), vec in zip(missing, emb_new):
                self._cache[keys[idx]] = vec
        if not texts:
            return np.zeros((0, 1), dtype=np.float32)
        return np.vstack([self._cache[k] for k in keys]).astype(np.float32)

    def _encode_uncached(self, texts: list[str]) -> np.ndarray:
        if self._backend == "hashing":
            dim = 256
            out = np.zeros((len(texts), dim), dtype=np.float32)
            for i, text in enumerate(texts):
                for tok in tokenize(text):
                    h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                    out[i, h % dim] += 1.0
            return self._normalise(out)
        if self._backend == "sentence_transformers":
            emb = self._model.encode(texts, batch_size=self.config.embed_batch_size,
                                     convert_to_numpy=True, show_progress_bar=False)
        else:  # pragma: no cover - exercised only without sentence-transformers
            import torch
            vecs = []
            with torch.no_grad():
                for i in range(0, len(texts), self.config.embed_batch_size):
                    batch = texts[i: i + self.config.embed_batch_size]
                    enc = self._tok(batch, padding=True, truncation=True, max_length=512,
                                    return_tensors="pt")
                    out = self._model(**enc).last_hidden_state
                    mask = enc["attention_mask"].unsqueeze(-1).float()
                    pooled = (out * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
                    vecs.append(pooled.cpu().numpy())
            emb = np.vstack(vecs) if vecs else np.zeros((0, 1), dtype=np.float32)
        return self._normalise(np.asarray(emb, dtype=np.float32))

    def fit(self, entities: Iterable[Entity]) -> "DenseRetriever":
        ents = list(entities)
        self._ids = [e.id for e in ents]
        if ents:
            self._matrix = self.encode([e.search_text(self.config.embed_max_chars) for e in ents])
        else:
            self._matrix = np.zeros((0, 1), dtype=np.float32)
        return self

    def score(self, query: str) -> dict[str, float]:
        if self._matrix is None:
            raise RuntimeError("DenseRetriever.fit() must be called first")
        if not self._ids or not query.strip():
            return {i: 0.0 for i in self._ids}
        q = self.encode([query])[0]
        sims = self._matrix @ q
        return {doc_id: float(s) for doc_id, s in zip(self._ids, sims)}


# --------------------------------------------------------------------------- #
# Path / filename
# --------------------------------------------------------------------------- #
class PathRetriever:
    """Ranks entities by token overlap between the query and their path/name tokens."""

    def __init__(self, config: RetrievalConfig | None = None):
        self.config = config or RetrievalConfig()
        self._ids: list[str] = []
        self._tokens: dict[str, set[str]] = {}

    def fit(self, entities: Iterable[Entity]) -> "PathRetriever":
        for ent in entities:
            self._ids.append(ent.id)
            key = f"{ent.file} {ent.qualname} {ent.name}"
            self._tokens[ent.id] = set(tokenize(key))
        return self

    def score(self, query: str) -> dict[str, float]:
        q = set(tokenize(query))
        if not q:
            return {i: 0.0 for i in self._ids}
        out = {}
        for i in self._ids:
            inter = len(q & self._tokens[i])
            out[i] = inter / math.sqrt(len(self._tokens[i]) + 1e-9) if inter else 0.0
        return out

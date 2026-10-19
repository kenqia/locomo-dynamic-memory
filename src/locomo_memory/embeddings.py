"""Lazy, pinned CPU MiniLM encoding with explicit length and vector checks."""

from threading import Lock

import numpy as np

from .config import Settings


class EmbeddingFailure(Exception):
    def __init__(self, code: str, status: int = 422):
        self.code = code
        self.status = status
        super().__init__(code)


def normalize_vectors(value, count: int, dimensions: int) -> np.ndarray:
    try:
        vectors = np.asarray(value, dtype=np.float32)
    except (TypeError, ValueError):
        raise EmbeddingFailure("invalid_embedding_vector") from None
    if vectors.shape != (count, dimensions) or not np.isfinite(vectors).all():
        raise EmbeddingFailure("invalid_embedding_vector")
    if count:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if not np.isfinite(norms).all() or np.any(norms <= 0):
            raise EmbeddingFailure("invalid_embedding_vector")
        vectors = vectors / norms
    return vectors


class MiniLMEmbedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._lock = Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError:
                    raise EmbeddingFailure("embedding_dependency_missing", 503) from None
                try:
                    self._model = SentenceTransformer(self.settings.embedding_model, revision=self.settings.embedding_revision, device="cpu", local_files_only=self.settings.embedding_local_files_only, trust_remote_code=False, token=False)
                except Exception:
                    raise EmbeddingFailure("embedding_model_unavailable", 503) from None
            if self._model.get_embedding_dimension() != self.settings.embedding_dimensions:
                raise EmbeddingFailure("embedding_dimension_mismatch")
            return self._model

    def identity(self) -> dict:
        model = self._load()
        return {"model": self.settings.embedding_model, "revision": self.settings.embedding_revision,
                "dimensions": self.settings.embedding_dimensions, "max_tokens": min(self.settings.embedding_max_tokens, model.max_seq_length),
                "length_policy": "reject", "normalized": True, "device": "cpu"}

    def encode(self, texts: list[str]) -> np.ndarray:
        model = self._load()
        limit = self.identity()["max_tokens"]
        for text in texts:
            # Check the exact enriched string passed to encode, with special tokens.
            tokens = model.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]
            if len(tokens) > limit:
                raise EmbeddingFailure("embedding_input_too_long")
        if not texts:
            return np.empty((0, self.settings.embedding_dimensions), dtype=np.float32)
        try:
            vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        except Exception:
            raise EmbeddingFailure("embedding_encode_failed", 503) from None
        return normalize_vectors(vectors, len(texts), self.settings.embedding_dimensions)

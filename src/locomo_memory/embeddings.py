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
        self._versions = {}

    def for_identity(self, identity: dict):
        """Select the exact persisted MiniLM encoder without loading current settings."""
        try:
            settings = Settings.model_validate({**self.settings.snapshot(),
                "embedding_model": identity["model"], "embedding_revision": identity["revision"],
                "embedding_dimensions": identity["dimensions"], "embedding_max_tokens": identity["max_tokens"],
                "embedding_local_files_only": True})
        except (ValueError, KeyError):
            raise EmbeddingFailure("embedding_identity_unavailable", 409) from None
        if all(getattr(self.settings, field) == getattr(settings, field) for field in ("embedding_model", "embedding_revision", "embedding_dimensions", "embedding_max_tokens")):
            if self.identity() != identity:
                raise EmbeddingFailure("embedding_identity_unavailable", 409)
            return self
        key = (settings.embedding_model, settings.embedding_revision, settings.embedding_max_tokens)
        with self._lock:
            encoder = self._versions.get(key)
            if encoder is None:
                encoder = MiniLMEmbedder(settings)
                self._versions[key] = encoder
        # Includes normalization, truncation policy and actual model dimension/limit.
        if encoder.identity() != identity:
            raise EmbeddingFailure("embedding_identity_unavailable", 409)
        return encoder

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

from __future__ import annotations

import logging
from typing import cast

import numpy as np
from tenacity import (
    Retrying,
    retry_unless_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import (
    DimensionMismatchError,
    EmbeddingAuthenticationError,
    EmbeddingUnavailableError,
)
from app.models.embedding import ChunkInput, Embedding
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Unified entry point for generating dense embeddings from text chunks."""

    def __init__(self, provider: EmbeddingProvider, config: EmbeddingConfig) -> None:
        self._provider = provider
        self._config = config

    def embed_query(self, text: str) -> list[float]:
        """Generate a single embedding for a query string.

        This is a convenience wrapper around :meth:`embed` that preserves the
        vector dimension and normalization configuration of the service.
        """
        embeddings = self.embed([ChunkInput(id="query", resource_id="query", text=text)])
        if not embeddings:
            return self._zero_vector()
        return embeddings[0].vector

    def embed(self, chunks: list[ChunkInput]) -> list[Embedding]:
        """Generate embeddings for ``chunks`` while preserving input order."""
        if not chunks:
            return []

        embeddings: list[Embedding] = []
        for batch in self._batches(chunks):
            embeddings.extend(self._embed_batch_with_fallback(batch))
        return embeddings

    def _batches(self, chunks: list[ChunkInput]) -> list[list[ChunkInput]]:
        """Split chunks into batches of size ``batch_size``."""
        batch_size = self._config.batch_size
        return [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]

    def _embed_batch_with_fallback(self, batch: list[ChunkInput]) -> list[Embedding]:
        """Embed a single batch, returning zero vectors for empty text chunks."""
        prepared = [(self._prepare_text(chunk.text), chunk) for chunk in batch]
        non_empty = [(idx, text, chunk) for idx, (text, chunk) in enumerate(prepared) if text]

        vectors: list[list[float]] = [self._zero_vector() for _ in batch]
        if non_empty:
            texts = [text for _, text, _ in non_empty]
            returned = self._embed_batch(texts)
            if len(returned) != len(non_empty):
                raise DimensionMismatchError(
                    f"Embedding provider 返回 {len(returned)} 个向量，" f"期望 {len(non_empty)} 个"
                )
            for (idx, _, _), vector in zip(non_empty, returned, strict=False):
                vectors[idx] = vector

        return [
            self._build_embedding(chunk, vector)
            for (_, chunk), vector in zip(prepared, vectors, strict=False)
        ]

    def _prepare_text(self, text: str) -> str:
        """Trim and truncate text so the provider API can safely process it."""
        text = text.strip()
        if not text:
            return ""
        max_chars = self._config.max_text_chars
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call the provider for one batch with retries and exponential backoff."""
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._config.max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_unless_exception_type(EmbeddingAuthenticationError),
                reraise=True,
            ):
                with attempt:
                    return self._provider.embed(texts)
        except EmbeddingAuthenticationError:
            raise
        except Exception as exc:
            logger.exception("Embedding provider failed after retries")
            raise EmbeddingUnavailableError() from exc
        return []  # pragma: no cover - unreachable, keeps mypy happy

    def _build_embedding(self, chunk: ChunkInput, vector: list[float]) -> Embedding:
        """Validate dimensions and normalize the vector before wrapping it."""
        if len(vector) != self._config.dimensions:
            raise DimensionMismatchError(
                f"向量维度 {len(vector)} 与配置 {self._config.dimensions} 不符"
            )

        final_vector = self._normalize(vector) if self._config.normalize else vector
        return Embedding(
            chunk_id=chunk.id,
            resource_id=chunk.resource_id,
            vector=final_vector,
            model=self._config.model,
            dimensions=len(final_vector),
        )

    def _normalize(self, vector: list[float]) -> list[float]:
        """L2-normalize ``vector``; return the original vector if its norm is zero."""
        arr = np.array(vector, dtype=float)
        norm = float(np.linalg.norm(arr))
        if norm == 0:
            return vector
        normalized = np.divide(arr, norm)
        return cast(list[float], normalized.tolist())

    def _zero_vector(self) -> list[float]:
        """Return a zero vector matching the configured dimensions."""
        return [0.0] * self._config.dimensions

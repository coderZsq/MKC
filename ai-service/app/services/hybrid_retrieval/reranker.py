from __future__ import annotations

import logging
from typing import Any

from app.models.hybrid_retrieval import SearchResult

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-Encoder reranker wrapping ``sentence-transformers``.

    The underlying ``CrossEncoder`` is loaded lazily on the first
    :meth:`rerank` call (or skipped entirely when ``enabled=False``) so that
    constructing the service never blocks on model download. Tests may inject a
    fake ``model`` exposing a ``predict(pairs)`` method to avoid loading any
    real weights.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: str = "cpu",
        max_length: int = 512,
        enabled: bool = True,
        model: Any | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._max_length = max_length
        self._enabled = enabled
        self._model: Any | None = model if enabled else None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
    ) -> list[SearchResult]:
        """Score ``(query, text)`` pairs with the cross-encoder and return Top-N.

        When disabled or empty, candidates are returned truncated to ``top_n``
        unchanged. Returned chunks carry ``source="rerank"`` and the model's
        raw score.
        """
        if not candidates or not self._enabled:
            return candidates[:top_n]

        self._ensure_model()
        if self._model is None:
            return candidates[:top_n]

        pairs = [(query, candidate.text) for candidate in candidates]
        raw_scores = self._model.predict(pairs)
        ranked = sorted(
            zip(candidates, raw_scores, strict=True),
            key=lambda item: float(item[1]),
            reverse=True,
        )[:top_n]
        return [
            candidate.model_copy(update={"score": float(score), "source": "rerank"})
            for candidate, score in ranked
        ]

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder

        logger.info("Loading reranker model %s on %s", self._model_name, self._device)
        self._model = CrossEncoder(
            self._model_name,
            device=self._device,
            max_length=self._max_length,
        )

from __future__ import annotations

from app.services.embedding.config import EmbeddingConfig


class MockEmbeddingProvider:
    """Deterministic embedding provider for local development and CI.

    Returns fixed-dimension vectors so downstream consumers can exercise the
    embedding pipeline without calling a remote API.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a deterministic vector for each text in ``texts``."""
        dimensions = self._config.dimensions
        return [[0.01 * (index + 1)] * dimensions for index in range(len(texts))]

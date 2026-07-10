from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for an embedding provider that maps texts to dense vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...  # noqa: D102

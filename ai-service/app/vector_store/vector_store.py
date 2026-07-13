from __future__ import annotations

from typing import Any, Protocol

from app.models.vector_record import VectorRecord, VectorSearchResult


class VectorStore(Protocol):
    """Abstract interface for vector storage backends."""

    def upsert(self, records: list[VectorRecord]) -> int: ...  # noqa: D102

    def delete_by_resource(
        self,
        resource_id: str,
        user_id: str | None = None,
    ) -> int: ...  # noqa: D102

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]: ...  # noqa: D102

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[VectorSearchResult]:
        """Fetch records matching ``filters`` without vector similarity.

        Used by hybrid retrieval to load the BM25 corpus. Results have
        ``score`` set to ``0.0`` since no similarity ranking is performed.
        """
        ...  # noqa: D102

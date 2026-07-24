from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.retrieval import RetrievalRequest, RetrievalResult


@runtime_checkable
class RagEngine(Protocol):
    """Unified retrieval contract consumed by QAService."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...

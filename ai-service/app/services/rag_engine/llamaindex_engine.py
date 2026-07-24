from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.retrieval import RetrievalRequest, RetrievalResult

if TYPE_CHECKING:
    from app.services.llamaindex.retrieval_engine import LlamaIndexRetrievalEngine


class LlamaIndexRagEngine:
    """RagEngine wrapper for the LlamaIndex retrieval engine."""

    def __init__(self, retrieval_engine: LlamaIndexRetrievalEngine) -> None:
        self._retrieval_engine = retrieval_engine

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return self._retrieval_engine.retrieve(request)

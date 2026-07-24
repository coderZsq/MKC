from __future__ import annotations

from app.models.retrieval import RetrievalRequest, RetrievalResult
from app.services.llamaindex.retrieval_engine import LlamaIndexRetrievalEngine


class LlamaIndexQueryEngine:
    """Query facade that prepares retrieval context without generating answers."""

    def __init__(self, retrieval_engine: LlamaIndexRetrievalEngine) -> None:
        self._retrieval_engine = retrieval_engine

    def query(self, request: RetrievalRequest) -> RetrievalResult:
        return self._retrieval_engine.retrieve(request)

from __future__ import annotations

from app.models.retrieval import RetrievalRequest, RetrievalResult
from app.services.retrieval.retrieval_service import RetrievalService


class LegacyRagEngine:
    """RagEngine wrapper for the existing legacy retrieval service."""

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return self._retrieval_service.retrieve(request)

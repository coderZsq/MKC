from __future__ import annotations

from app.models.retrieval import RetrievalChunk, RetrievalRequest
from app.services.retrieval.retrieval_service import RetrievalService


class RetrievalTool:
    """Thin tool wrapper around the S3-4 RetrievalService."""

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval = retrieval_service

    async def invoke(
        self,
        *,
        question: str,
        user_id: str,
        resource_ids: list[str],
        top_k: int | None = None,
        score_threshold: float | None = None,
        max_context_tokens: int | None = None,
    ) -> list[RetrievalChunk]:
        request = RetrievalRequest(
            question=question,
            user_id=user_id,
            resource_ids=resource_ids,
            top_k=top_k or 5,
            score_threshold=score_threshold if score_threshold is not None else 0.7,
            max_context_tokens=max_context_tokens,
        )
        result = self._retrieval.retrieve(request)
        return result.chunks

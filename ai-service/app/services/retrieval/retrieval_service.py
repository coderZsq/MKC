from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.core.exceptions import (
    APIException,
    RetrievalForbiddenError,
    RetrievalUnavailableError,
)
from app.models.retrieval import RetrievalChunk, RetrievalRequest, RetrievalResult
from app.models.vector_record import VectorSearchResult
from app.services.chunking.token_estimator import TokenEstimator
from app.services.retrieval.prompt_builder import PromptBuilder


@dataclass(frozen=True)
class RetrievalConfig:
    """Runtime configuration for the retrieval service."""

    default_top_k: int = 5
    score_threshold: float = 0.7
    max_context_tokens: int = 4096
    prompt_template: str = "prompts/rag.txt"


@runtime_checkable
class EmbeddingServiceProtocol(Protocol):
    """Minimal protocol needed by the retrieval service."""

    def embed_query(self, text: str) -> list[float]: ...  # noqa: D102


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Minimal protocol needed by the retrieval service."""

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]: ...  # noqa: D102


class RetrievalService:
    """Orchestrates embedding, vector search, filtering, and prompt assembly."""

    def __init__(
        self,
        embedding_svc: EmbeddingServiceProtocol,
        vector_store: VectorStoreProtocol,
        prompt_builder: PromptBuilder,
        config: RetrievalConfig,
        token_estimator: TokenEstimator | None = None,
    ) -> None:
        self._embedding_svc = embedding_svc
        self._vector_store = vector_store
        self._prompt_builder = prompt_builder
        self._config = config
        self._token_estimator = token_estimator or TokenEstimator()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve relevant chunks and assemble a prompt for the question."""
        query_vector = self._embedding_svc.embed_query(request.question)
        top_k = request.top_k or self._config.default_top_k
        score_threshold = (
            request.score_threshold
            if request.score_threshold is not None
            else self._config.score_threshold
        )
        max_context_tokens = (
            request.max_context_tokens
            if request.max_context_tokens is not None
            else self._config.max_context_tokens
        )

        try:
            search_results = self._vector_store.search(
                vector=query_vector,
                top_k=top_k,
                filters={
                    "user_id": request.user_id,
                    "resource_ids": request.resource_ids,
                },
            )
        except APIException:
            raise
        except Exception as exc:
            raise RetrievalUnavailableError("检索不可用") from exc

        sorted_results = sorted(search_results, key=lambda result: result.score, reverse=True)
        filtered = [result for result in sorted_results if result.score >= score_threshold]
        self._validate_authorization(filtered, request.user_id, request.resource_ids)
        compressed, token_count = self._compress_context(filtered, max_context_tokens)
        prompt = self._prompt_builder.build(compressed, request.question)
        return RetrievalResult(
            chunks=compressed,
            prompt=prompt,
            context_token_count=token_count,
        )

    def _validate_authorization(
        self,
        chunks: list[VectorSearchResult],
        user_id: str,
        resource_ids: list[str],
    ) -> None:
        """Raise if the vector store returned chunks outside the requested scope.

        This is a defensive check: the vector store filter should already enforce
        the scope, but if a backend misbehaves we refuse to return the data.
        """
        allowed_resources = set(resource_ids)
        for chunk in chunks:
            if chunk.user_id != user_id or chunk.resource_id not in allowed_resources:
                raise RetrievalForbiddenError("无权访问资源")

    def _compress_context(
        self,
        chunks: list[VectorSearchResult],
        max_context_tokens: int,
    ) -> tuple[list[RetrievalChunk], int]:
        """Select chunks in relevance order until the token budget is reached.

        At least one chunk is always selected when chunks are available, even if
        it exceeds the budget, so that a highly relevant single chunk is not lost.
        """
        selected: list[RetrievalChunk] = []
        total_tokens = 0
        for chunk in chunks:
            chunk_tokens = self._token_estimator.count(chunk.text)
            if selected and total_tokens + chunk_tokens > max_context_tokens:
                break
            selected.append(
                RetrievalChunk(
                    chunk_id=chunk.id,
                    resource_id=chunk.resource_id,
                    text=chunk.text,
                    score=chunk.score,
                    metadata=chunk.metadata,
                ),
            )
            total_tokens += chunk_tokens
        return selected, total_tokens

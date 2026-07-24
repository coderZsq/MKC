from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from llama_index.core.schema import BaseNode, NodeWithScore

from app.core.exceptions import (
    APIException,
    InvalidRetrievalRequestError,
    LlamaIndexRetrievalForbiddenError,
    RetrievalUnavailableError,
)
from app.models.retrieval import RetrievalChunk, RetrievalRequest, RetrievalResult
from app.services.llamaindex.context_compressor import LlamaIndexContextCompressor
from app.services.llamaindex.metadata_mapper import (
    node_to_retrieval_chunk,
    node_with_score_to_chunk,
)
from app.services.retrieval.prompt_builder import PromptBuilder


@dataclass(frozen=True)
class LlamaIndexRetrievalConfig:
    """Runtime configuration for the LlamaIndex retrieval engine."""

    default_top_k: int = 5
    score_threshold: float = 0.7
    max_context_tokens: int = 4096
    per_resource_candidates: bool = True

    def __post_init__(self) -> None:
        if self.default_top_k <= 0:
            raise InvalidRetrievalRequestError("default_top_k 必须大于 0")
        if not 0.0 <= self.score_threshold <= 1.0:
            raise InvalidRetrievalRequestError("score_threshold 必须在 0 到 1 之间")
        if self.max_context_tokens <= 0:
            raise InvalidRetrievalRequestError("max_context_tokens 必须大于 0")


@runtime_checkable
class LlamaIndexRetrieverProtocol(Protocol):
    """Minimal retriever contract implemented by S6-4 adapters and tests."""

    def query(
        self,
        query: str,
        *,
        user_id: str,
        resource_ids: list[str],
        top_k: int = 10,
    ) -> list[BaseNode | NodeWithScore]: ...


class LlamaIndexRetrievalEngine:
    """RetrievalRequest -> RetrievalResult wrapper for the LlamaIndex RAG path."""

    def __init__(
        self,
        retriever: LlamaIndexRetrieverProtocol,
        prompt_builder: PromptBuilder,
        config: LlamaIndexRetrievalConfig | None = None,
        context_compressor: LlamaIndexContextCompressor | None = None,
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._config = config or LlamaIndexRetrievalConfig()
        self._context_compressor = context_compressor or LlamaIndexContextCompressor()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve scoped context chunks and build a prompt for the user question."""
        self._validate_request(request)
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
            nodes = self._retrieve_candidates(request, top_k)
        except APIException:
            raise
        except Exception as exc:
            raise RetrievalUnavailableError("检索不可用") from exc

        chunks = [self._node_to_chunk(node) for node in nodes]
        self._validate_authorization(chunks, request.user_id, request.resource_ids)
        chunks = sorted(chunks, key=lambda chunk: chunk.score, reverse=True)
        if self._should_use_per_resource_candidates(request.resource_ids):
            chunks = self._deduplicate_similar_chunks(chunks)
        filtered = [chunk for chunk in chunks if chunk.score >= score_threshold][:top_k]
        compressed, token_count = self._context_compressor.compress(
            filtered,
            max_context_tokens,
        )
        return RetrievalResult(
            chunks=compressed,
            prompt=self._prompt_builder.build(compressed, request.question),
            context_token_count=token_count,
        )

    def _retrieve_candidates(
        self,
        request: RetrievalRequest,
        top_k: int,
    ) -> list[BaseNode | NodeWithScore]:
        candidate_top_k = self._candidate_top_k(top_k, request.resource_ids)
        nodes = self._retriever.query(
            request.question,
            user_id=request.user_id,
            resource_ids=request.resource_ids,
            top_k=candidate_top_k,
        )
        if not self._should_use_per_resource_candidates(request.resource_ids):
            return nodes

        candidates = list(nodes)
        for resource_id in dict.fromkeys(request.resource_ids):
            candidates.extend(
                self._retriever.query(
                    request.question,
                    user_id=request.user_id,
                    resource_ids=[resource_id],
                    top_k=1,
                )
            )
        return candidates

    def _candidate_top_k(self, top_k: int, resource_ids: list[str]) -> int:
        if not self._should_use_per_resource_candidates(resource_ids):
            return top_k
        unique_count = len(set(resource_ids))
        return min(max(top_k * 8, top_k + unique_count), 100)

    def _should_use_per_resource_candidates(self, resource_ids: list[str]) -> bool:
        return self._config.per_resource_candidates and len(set(resource_ids)) > 1

    def _validate_authorization(
        self,
        chunks: list[RetrievalChunk],
        user_id: str,
        resource_ids: list[str],
    ) -> None:
        allowed_resources = set(resource_ids)
        for chunk in chunks:
            chunk_user_id = str(chunk.metadata.get("user_id") or "")
            if chunk_user_id != user_id or chunk.resource_id not in allowed_resources:
                raise LlamaIndexRetrievalForbiddenError("无权访问资源")

    def _deduplicate_similar_chunks(
        self,
        chunks: list[RetrievalChunk],
    ) -> list[RetrievalChunk]:
        seen: set[str] = set()
        deduped: list[RetrievalChunk] = []
        for chunk in chunks:
            fingerprint = self._chunk_fingerprint(chunk.text)
            key = fingerprint or f"{chunk.resource_id}:{chunk.chunk_id}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)
        return deduped

    @staticmethod
    def _node_to_chunk(node: BaseNode | NodeWithScore) -> RetrievalChunk:
        if isinstance(node, NodeWithScore):
            return node_with_score_to_chunk(node)
        return node_to_retrieval_chunk(node)

    @staticmethod
    def _validate_request(request: RetrievalRequest) -> None:
        if not request.question.strip():
            raise InvalidRetrievalRequestError("question 不能为空")
        if not request.user_id.strip():
            raise InvalidRetrievalRequestError("user_id 不能为空")
        if not request.resource_ids:
            raise InvalidRetrievalRequestError("resource_ids 不能为空")

    @staticmethod
    def _chunk_fingerprint(text: str) -> str:
        normalized = re.sub(r"\s+", "", text).strip()
        if not normalized:
            return ""
        return hashlib.sha1(normalized[:1200].encode("utf-8")).hexdigest()

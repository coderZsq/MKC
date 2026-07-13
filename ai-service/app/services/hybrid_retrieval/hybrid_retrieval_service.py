from __future__ import annotations

import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.exceptions import (
    APIException,
    RetrievalForbiddenError,
    RetrievalUnavailableError,
)
from app.models.hybrid_retrieval import (
    FusionStats,
    HybridRetrievalRequest,
    HybridRetrievalResult,
    SearchResult,
    SearchSource,
)
from app.models.vector_record import VectorSearchResult
from app.services.hybrid_retrieval.rrf import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HybridRetrievalConfig:
    """Runtime configuration for the hybrid retrieval service.

    The nested ``bm25`` / ``reranker`` YAML sections are flattened here for
    ergonomic access; :func:`build_hybrid_retrieval_config` performs the
    mapping.
    """

    bm25_weight: float = 1.0
    vector_weight: float = 1.0
    rrf_k: int = 60
    rerank_top_n: int = 20
    final_top_k: int = 5
    score_threshold: float = 0.0
    timeout_ms: int = 800
    fallback_to_vector: bool = True
    bm25_tokenizer: str = "jieba"
    bm25_user_dict: str = ""
    bm25_cache_index: bool = True
    bm25_max_docs: int = 1000
    bm25_cache_max_entries: int = 100
    reranker_model_name: str = "BAAI/bge-reranker-base"
    reranker_device: str = "cpu"
    reranker_max_length: int = 512
    reranker_enabled: bool = True


@dataclass(frozen=True)
class _ResolvedParams:
    """Request parameters after merging request overrides with config."""

    bm25_weight: float
    vector_weight: float
    rrf_k: int
    rerank_top_n: int
    final_top_k: int
    score_threshold: float
    timeout_ms: int
    fallback_to_vector: bool
    bm25_max_docs: int
    bm25_cache_max_entries: int
    reranker_enabled: bool


class EmbeddingServiceProtocol(Protocol):
    """Minimal embedding service contract required by hybrid retrieval."""

    def embed_query(self, text: str) -> list[float]: ...  # noqa: D102


class VectorStoreProtocol(Protocol):
    """Minimal vector store contract required by hybrid retrieval."""

    def search(  # noqa: D102
        self,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]: ...

    def query(  # noqa: D102
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[VectorSearchResult]: ...


class BM25StoreProtocol(Protocol):
    """BM25 store contract used by hybrid retrieval."""

    def index(self, docs: list[SearchResult]) -> None: ...  # noqa: D102

    def search(  # noqa: D102
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...


class RerankerProtocol(Protocol):
    """Reranker contract used by hybrid retrieval."""

    def rerank(  # noqa: D102
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
    ) -> list[SearchResult]: ...


class HybridRetrievalService:
    """Orchestrates BM25 + vector retrieval, RRF fusion, and cross-encoder reranking.

    Each retrieval path is isolated so a single failure degrades gracefully
    rather than aborting the whole request. An injectable ``clock`` makes the
    overall-timeout fallback deterministic in tests.
    """

    def __init__(
        self,
        bm25_store_factory: Callable[[], BM25StoreProtocol],
        embedding_svc: EmbeddingServiceProtocol,
        vector_store: VectorStoreProtocol,
        reranker: RerankerProtocol,
        config: HybridRetrievalConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._bm25_store_factory = bm25_store_factory
        self._embedding_svc = embedding_svc
        self._vector_store = vector_store
        self._reranker = reranker
        self._config = config
        self._clock = clock
        self._bm25_cache: OrderedDict[str, BM25StoreProtocol] = OrderedDict()

    def retrieve(self, request: HybridRetrievalRequest) -> HybridRetrievalResult:
        """Run the hybrid retrieval pipeline and return the reranked Top-K."""
        start = self._clock()
        params = self._resolve_params(request)
        filters: dict[str, Any] = {
            "user_id": request.user_id,
            "resource_ids": request.resource_ids,
        }

        bm25_hits, bm25_failed = self._bm25_retrieve(request, params, filters)
        vector_hits, vector_failed = self._vector_retrieve(request, params, filters)
        degraded = bm25_failed or vector_failed

        if bm25_failed and vector_failed:
            raise RetrievalUnavailableError("混合检索两路均失败，无法降级")

        fusion = FusionStats(
            bm25_count=len(bm25_hits),
            vector_count=len(vector_hits),
            fused_count=0,
        )
        if not bm25_hits and not vector_hits:
            return HybridRetrievalResult(
                chunks=[],
                fusion=fusion,
                degraded=degraded,
                elapsed_ms=self._elapsed_ms(start),
            )

        fused = reciprocal_rank_fusion(
            bm25_hits,
            vector_hits,
            bm25_weight=params.bm25_weight,
            vector_weight=params.vector_weight,
            k=params.rrf_k,
        )
        fused_top = fused[: params.rerank_top_n]
        fusion = FusionStats(
            bm25_count=len(bm25_hits),
            vector_count=len(vector_hits),
            fused_count=len(fused),
        )

        if self._elapsed_ms(start) >= params.timeout_ms:
            degraded = True
            chunks = self._timeout_fallback_chunks(params, vector_hits, fused_top)
        elif params.reranker_enabled:
            chunks, rerank_failed = self._rerank_chunks(request.question, fused_top, params)
            degraded = degraded or rerank_failed
        else:
            chunks = fused_top[: params.final_top_k]

        return self._finalize_result(
            chunks,
            fusion,
            request,
            params,
            degraded,
            start,
        )

    def _timeout_fallback_chunks(
        self,
        params: _ResolvedParams,
        vector_hits: list[SearchResult],
        fused_top: list[SearchResult],
    ) -> list[SearchResult]:
        """Return chunks when the overall timeout fires before reranking."""
        if params.fallback_to_vector and vector_hits:
            return [
                hit.model_copy(
                    update={
                        "score": float(hit.score),
                        "source": "vector",
                        "metadata": dict(hit.metadata),
                    },
                )
                for hit in vector_hits[: params.final_top_k]
            ]
        return fused_top[: params.final_top_k]

    def _rerank_chunks(
        self,
        question: str,
        fused_top: list[SearchResult],
        params: _ResolvedParams,
    ) -> tuple[list[SearchResult], bool]:
        """Rerank fused candidates, returning (chunks, failed)."""
        try:
            return (
                self._reranker.rerank(question, fused_top, params.final_top_k),
                False,
            )
        except APIException:
            raise
        except Exception:
            logger.warning("Rerank failed, falling back to RRF Top-K", exc_info=True)
            return fused_top[: params.final_top_k], True

    def _finalize_result(
        self,
        chunks: list[SearchResult],
        fusion: FusionStats,
        request: HybridRetrievalRequest,
        params: _ResolvedParams,
        degraded: bool,
        start: float,
    ) -> HybridRetrievalResult:
        """Validate authorization, apply score threshold, and build the result."""
        self._validate_authorization(chunks, request.user_id, request.resource_ids)
        filtered = [chunk for chunk in chunks if chunk.score >= params.score_threshold]
        return HybridRetrievalResult(
            chunks=filtered,
            fusion=fusion,
            degraded=degraded,
            elapsed_ms=self._elapsed_ms(start),
        )

    def _resolve_params(self, request: HybridRetrievalRequest) -> _ResolvedParams:
        cfg = self._config
        return _ResolvedParams(
            bm25_weight=request.bm25_weight if request.bm25_weight is not None else cfg.bm25_weight,
            vector_weight=(
                request.vector_weight if request.vector_weight is not None else cfg.vector_weight
            ),
            rrf_k=request.rrf_k if request.rrf_k is not None else cfg.rrf_k,
            rerank_top_n=(
                request.rerank_top_n if request.rerank_top_n is not None else cfg.rerank_top_n
            ),
            final_top_k=(
                request.final_top_k if request.final_top_k is not None else cfg.final_top_k
            ),
            score_threshold=(
                request.score_threshold
                if request.score_threshold is not None
                else cfg.score_threshold
            ),
            timeout_ms=request.timeout_ms if request.timeout_ms is not None else cfg.timeout_ms,
            fallback_to_vector=cfg.fallback_to_vector,
            bm25_max_docs=cfg.bm25_max_docs,
            bm25_cache_max_entries=cfg.bm25_cache_max_entries,
            reranker_enabled=cfg.reranker_enabled,
        )

    def _bm25_retrieve(
        self,
        request: HybridRetrievalRequest,
        params: _ResolvedParams,
        filters: dict[str, Any],
    ) -> tuple[list[SearchResult], bool]:
        try:
            store = self._get_or_build_bm25(filters, params)
            hits = store.search(request.question, params.rerank_top_n, filters)
            return hits, False
        except APIException:
            raise
        except Exception:
            logger.warning("BM25 retrieval path failed", exc_info=True)
            return [], True

    def _vector_retrieve(
        self,
        request: HybridRetrievalRequest,
        params: _ResolvedParams,
        filters: dict[str, Any],
    ) -> tuple[list[SearchResult], bool]:
        try:
            query_vector = self._embedding_svc.embed_query(request.question)
            results = self._vector_store.search(
                query_vector,
                params.rerank_top_n,
                filters=filters,
            )
            return [_to_search_result(hit, source="vector") for hit in results], False
        except APIException:
            raise
        except Exception:
            logger.warning("Vector retrieval path failed", exc_info=True)
            return [], True

    def _get_or_build_bm25(
        self,
        filters: dict[str, Any],
        params: _ResolvedParams,
    ) -> BM25StoreProtocol:
        cache_key = _bm25_cache_key(filters)
        if self._config.bm25_cache_index and cache_key in self._bm25_cache:
            self._bm25_cache.move_to_end(cache_key)
            return self._bm25_cache[cache_key]

        docs = self._load_corpus(filters, params.bm25_max_docs)
        store = self._bm25_store_factory()
        store.index(docs)
        if self._config.bm25_cache_index:
            self._bm25_cache[cache_key] = store
            self._bm25_cache.move_to_end(cache_key)
            self._evict_bm25_cache(params.bm25_cache_max_entries)
        return store

    def _evict_bm25_cache(self, max_entries: int) -> None:
        while len(self._bm25_cache) > max_entries:
            self._bm25_cache.popitem(last=False)

    def _load_corpus(
        self,
        filters: dict[str, Any],
        max_docs: int,
    ) -> list[SearchResult]:
        records = self._vector_store.query(filters=filters, limit=max_docs)
        return [_to_search_result(record, source="bm25") for record in records]

    def _validate_authorization(
        self,
        chunks: list[SearchResult],
        user_id: str,
        resource_ids: list[str],
    ) -> None:
        """Defensively reject chunks outside the requested user/resource scope.

        The vector store filter should already enforce scope; this guard
        catches backend bugs so unauthorized data is never returned.
        """
        allowed_resources = set(resource_ids)
        for chunk in chunks:
            if chunk.user_id != user_id or chunk.resource_id not in allowed_resources:
                raise RetrievalForbiddenError("无权访问资源")

    def _elapsed_ms(self, start: float) -> int:
        return int((self._clock() - start) * 1000)


def _to_search_result(record: VectorSearchResult, source: SearchSource) -> SearchResult:
    return SearchResult(
        chunk_id=record.id,
        resource_id=record.resource_id,
        user_id=record.user_id,
        text=record.text,
        score=record.score,
        source=source,
        metadata=dict(record.metadata),
    )


def _bm25_cache_key(filters: dict[str, Any]) -> str:
    user_id = str(filters.get("user_id", ""))
    resource_ids = filters.get("resource_ids", [])
    if isinstance(resource_ids, str):
        resource_ids = [resource_ids]
    sorted_ids = ",".join(sorted(str(rid) for rid in resource_ids))
    return f"{user_id}|{sorted_ids}"

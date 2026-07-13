from __future__ import annotations

import time

import pytest

from app.core.exceptions import RetrievalForbiddenError, RetrievalUnavailableError
from app.models.hybrid_retrieval import HybridRetrievalRequest, SearchResult
from app.models.vector_record import VectorSearchResult
from app.services.hybrid_retrieval.hybrid_retrieval_service import (
    HybridRetrievalConfig,
    HybridRetrievalService,
)

# ---------------------------- fakes ----------------------------


class _FakeEmbedding:
    def __init__(self, vector: tuple[float, ...] = (0.1, 0.2, 0.3)) -> None:
        self._vector = list(vector)
        self.calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        return list(self._vector)


class _FakeVectorStore:
    def __init__(
        self,
        search_results: list[VectorSearchResult] | None = None,
        query_results: list[VectorSearchResult] | None = None,
        search_raises: bool = False,
    ) -> None:
        self._search_results = search_results or []
        self._query_results = query_results or []
        self._search_raises = search_raises
        self.search_calls: list[tuple] = []
        self.query_calls: list[tuple] = []

    def search(self, vector, top_k=10, filters=None):
        self.search_calls.append((vector, top_k, filters))
        if self._search_raises:
            raise RuntimeError("vector store down")
        return list(self._search_results)

    def query(self, filters=None, limit=1000):
        self.query_calls.append((filters, limit))
        return list(self._query_results)


class _FakeBM25Store:
    def __init__(
        self,
        search_results: list[SearchResult] | None = None,
        search_raises: bool = False,
    ) -> None:
        self._search_results = search_results or []
        self._search_raises = search_raises
        self.index_calls: list[list] = []
        self.search_calls: list[tuple] = []

    def index(self, docs):
        self.index_calls.append(list(docs))

    def search(self, query, top_k, filters=None):
        self.search_calls.append((query, top_k, filters))
        if self._search_raises:
            raise RuntimeError("bm25 down")
        return list(self._search_results)


class _FakeReranker:
    def __init__(
        self,
        rerank_results: list[SearchResult] | None = None,
        raises: bool = False,
    ) -> None:
        self._rerank_results = rerank_results
        self._raises = raises
        self.calls: list[tuple] = []

    def rerank(self, query, candidates, top_n):
        self.calls.append((query, list(candidates), top_n))
        if self._raises:
            raise RuntimeError("rerank down")
        if self._rerank_results is not None:
            return list(self._rerank_results)
        return list(candidates[:top_n])


class _ScriptedClock:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._i = 0

    def __call__(self) -> float:
        v = self._values[min(self._i, len(self._values) - 1)]
        self._i += 1
        return v


# ---------------------------- helpers ----------------------------


def _config(**overrides) -> HybridRetrievalConfig:
    defaults = {
        "bm25_weight": 1.0,
        "vector_weight": 1.0,
        "rrf_k": 60,
        "rerank_top_n": 20,
        "final_top_k": 5,
        "score_threshold": 0.0,
        "timeout_ms": 800,
        "fallback_to_vector": True,
        "bm25_tokenizer": "whitespace",
        "bm25_user_dict": "",
        "bm25_cache_index": True,
        "bm25_max_docs": 1000,
        "bm25_cache_max_entries": 100,
        "reranker_model_name": "fake",
        "reranker_device": "cpu",
        "reranker_max_length": 512,
        "reranker_enabled": True,
    }
    defaults.update(overrides)
    return HybridRetrievalConfig(**defaults)


def _request(**overrides) -> HybridRetrievalRequest:
    defaults = {"question": "quick fox", "user_id": "user-1", "resource_ids": ["res-1"]}
    defaults.update(overrides)
    return HybridRetrievalRequest(**defaults)


def _vsr(
    chunk_id: str,
    resource_id: str = "res-1",
    user_id: str = "user-1",
    text: str = "",
    score: float = 0.9,
) -> VectorSearchResult:
    return VectorSearchResult(
        id=chunk_id,
        resource_id=resource_id,
        user_id=user_id,
        text=text or chunk_id,
        metadata={},
        score=score,
    )


def _sr(
    chunk_id: str,
    resource_id: str = "res-1",
    user_id: str = "user-1",
    text: str = "",
    score: float = 0.5,
    source: str = "bm25",
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        resource_id=resource_id,
        user_id=user_id,
        text=text or chunk_id,
        score=score,
        source=source,  # type: ignore[arg-type]
        metadata={},
    )


class _Harness:
    def __init__(self, **kw) -> None:
        self.embedding = kw.get("embedding", _FakeEmbedding())
        self.vector_store = kw.get("vector_store", _FakeVectorStore())
        bm25_results = kw.get("bm25_results")
        bm25_raises = kw.get("bm25_raises", False)
        self.factory_calls = 0

        def factory():
            self.factory_calls += 1
            return _FakeBM25Store(search_results=bm25_results, search_raises=bm25_raises)

        self.reranker = _FakeReranker(
            rerank_results=kw.get("reranker_results"),
            raises=kw.get("reranker_raises", False),
        )
        self.config = kw.get("config", _config())
        clock = kw.get("clock") or time.monotonic
        self.service = HybridRetrievalService(
            factory,
            self.embedding,
            self.vector_store,
            self.reranker,
            self.config,
            clock,
        )


# ---------------------------- tests ----------------------------


# MKC-TC-S4-7-001: happy path - both paths, RRF fusion, rerank, non-degraded.
def test_happy_path_fuses_and_reranks() -> None:
    h = _Harness(
        bm25_results=[_sr("c1", score=0.5), _sr("c2", score=0.3)],
        vector_store=_FakeVectorStore(search_results=[_vsr("c2"), _vsr("c3")]),
    )

    result = h.service.retrieve(_request())

    assert len(result.chunks) >= 1
    assert result.fusion.bm25_count == 2
    assert result.fusion.vector_count == 2
    assert result.fusion.fused_count == 3  # c2 deduped
    assert result.degraded is False
    assert result.elapsed_ms >= 0
    assert len(h.reranker.calls) == 1


# MKC-TC-S4-7-003: RRF dedups overlapping chunk_ids across paths.
def test_fusion_dedups_overlapping_chunks() -> None:
    h = _Harness(
        bm25_results=[_sr("c1"), _sr("c2")],
        vector_store=_FakeVectorStore(search_results=[_vsr("c2"), _vsr("c3")]),
    )

    result = h.service.retrieve(_request())

    assert result.fusion.fused_count == 3
    chunk_ids = {c.chunk_id for c in result.chunks}
    assert chunk_ids <= {"c1", "c2", "c3"}


# MKC-TC-S4-7-006: vector path reuses embedding + vector store with filters.
def test_vector_path_uses_embedding_and_filters() -> None:
    h = _Harness(
        bm25_results=[],
        vector_store=_FakeVectorStore(search_results=[_vsr("c1")]),
    )

    h.service.retrieve(_request())

    assert h.embedding.calls == ["quick fox"]
    assert len(h.vector_store.search_calls) == 1
    vector, top_k, filters = h.vector_store.search_calls[0]
    assert vector == [0.1, 0.2, 0.3]
    assert filters == {"user_id": "user-1", "resource_ids": ["res-1"]}


# MKC-TC-S4-7-010: reranker receives fused Top-N and result is capped at final_top_k.
def test_rerank_receives_fused_top_and_caps_result() -> None:
    h = _Harness(
        bm25_results=[_sr("c1"), _sr("c2"), _sr("c3")],
        vector_store=_FakeVectorStore(),
        config=_config(rerank_top_n=10, final_top_k=2),
    )

    result = h.service.retrieve(_request())

    assert len(h.reranker.calls) == 1
    _query, candidates, top_n = h.reranker.calls[0]
    assert top_n == 2
    assert len(candidates) == 3
    assert len(result.chunks) <= 2


# MKC-TC-S4-7-016: BM25 failure degrades to vector-only.
def test_bm25_failure_degrades_to_vector_only() -> None:
    h = _Harness(
        bm25_raises=True,
        vector_store=_FakeVectorStore(search_results=[_vsr("c2")]),
    )

    result = h.service.retrieve(_request())

    assert result.degraded is True
    assert result.fusion.bm25_count == 0
    assert result.fusion.vector_count == 1
    assert len(result.chunks) >= 1


# MKC-TC-S4-7-021: vector failure degrades to BM25-only.
def test_vector_failure_degrades_to_bm25_only() -> None:
    h = _Harness(
        bm25_results=[_sr("c1")],
        vector_store=_FakeVectorStore(search_raises=True),
    )

    result = h.service.retrieve(_request())

    assert result.degraded is True
    assert result.fusion.bm25_count == 1
    assert result.fusion.vector_count == 0
    assert len(result.chunks) >= 1


# MKC-TC-S4-7-026: both paths fail -> 503 RetrievalUnavailableError.
def test_both_paths_fail_raises_unavailable() -> None:
    h = _Harness(
        bm25_raises=True,
        vector_store=_FakeVectorStore(search_raises=True),
    )

    with pytest.raises(RetrievalUnavailableError):
        h.service.retrieve(_request())


# MKC-TC-S4-7-024: both paths empty (no failure) -> empty 200, not degraded.
def test_both_paths_empty_returns_empty_not_degraded() -> None:
    h = _Harness(bm25_results=[], vector_store=_FakeVectorStore(search_results=[]))

    result = h.service.retrieve(_request())

    assert result.chunks == []
    assert result.fusion.bm25_count == 0
    assert result.fusion.vector_count == 0
    assert result.fusion.fused_count == 0
    assert result.degraded is False
    assert len(h.reranker.calls) == 0


# MKC-TC-S4-7-022: rerank failure falls back to RRF Top-K, degraded.
def test_rerank_failure_falls_back_to_rrf_topk() -> None:
    h = _Harness(
        bm25_results=[_sr("c1"), _sr("c2")],
        vector_store=_FakeVectorStore(search_results=[_vsr("c3")]),
        reranker_raises=True,
        config=_config(final_top_k=2),
    )

    result = h.service.retrieve(_request())

    assert result.degraded is True
    assert len(h.reranker.calls) == 1
    assert len(result.chunks) <= 2
    # RRF sources preserved (rerank did not tag them).
    assert all(c.source in ("bm25", "vector") for c in result.chunks)


# MKC-TC-S4-7-023: score_threshold filters out low-scoring reranked chunks.
def test_score_threshold_filters_low_scores() -> None:
    rerank_results = [
        _sr("c1", score=0.9, source="rerank"),
        _sr("c2", score=0.5, source="rerank"),
        _sr("c3", score=0.1, source="rerank"),
    ]
    h = _Harness(
        bm25_results=[_sr("c1"), _sr("c2"), _sr("c3")],
        vector_store=_FakeVectorStore(),
        reranker_results=rerank_results,
        config=_config(final_top_k=3, score_threshold=0.4),
    )

    result = h.service.retrieve(_request())

    assert {c.chunk_id for c in result.chunks} == {"c1", "c2"}
    assert all(c.score >= 0.4 for c in result.chunks)


# MKC-TC-S4-7-025: overall timeout degrades to pure vector, reranker skipped.
def test_timeout_degrades_to_pure_vector_and_skips_rerank() -> None:
    clock = _ScriptedClock([0.0, 1000.0, 1000.0])
    h = _Harness(
        bm25_results=[_sr("c1")],
        vector_store=_FakeVectorStore(search_results=[_vsr("c1"), _vsr("c2")]),
        config=_config(timeout_ms=800, final_top_k=5, fallback_to_vector=True),
        clock=clock,
    )

    result = h.service.retrieve(_request())

    assert result.degraded is True
    assert len(h.reranker.calls) == 0
    assert {c.chunk_id for c in result.chunks} == {"c1", "c2"}
    assert all(c.source == "vector" for c in result.chunks)


# MKC-TC-S4-7-027: reranker disabled -> RRF Top-K, not degraded, rerank skipped.
def test_reranker_disabled_returns_rrf_topk_not_degraded() -> None:
    h = _Harness(
        bm25_results=[_sr("c1")],
        vector_store=_FakeVectorStore(search_results=[_vsr("c2")]),
        config=_config(reranker_enabled=False, final_top_k=2),
    )

    result = h.service.retrieve(_request())

    assert result.degraded is False
    assert len(h.reranker.calls) == 0
    assert all(c.source in ("bm25", "vector") for c in result.chunks)


# MKC-TC-S4-7-032: request omits params -> config defaults applied.
def test_config_defaults_applied_when_request_omits_params() -> None:
    h = _Harness(
        bm25_results=[_sr("c1")],
        vector_store=_FakeVectorStore(search_results=[_vsr("c2")]),
        config=_config(rerank_top_n=10, final_top_k=3),
    )

    h.service.retrieve(_request())  # no param overrides

    # BM25 search uses config rerank_top_n; reranker uses config final_top_k.
    assert h.vector_store.search_calls[0][1] == 10
    # The cached BM25 store is the one created by the factory.
    bm25_store = h.service._bm25_cache  # type: ignore[attr-defined]
    cached = next(iter(bm25_store.values()))
    assert cached.search_calls[0][1] == 10  # type: ignore[attr-defined]
    assert h.reranker.calls[0][2] == 3


# MKC-TC-S4-7-036: BM25 index cached by (user_id, sorted resource_ids).
def test_bm25_index_cached_across_calls() -> None:
    h = _Harness(
        bm25_results=[_sr("c1")],
        vector_store=_FakeVectorStore(
            search_results=[_vsr("c2")],
            query_results=[_vsr("c1")],  # corpus for BM25 indexing
        ),
    )

    h.service.retrieve(_request())
    h.service.retrieve(_request())  # same user + resource -> cache hit

    assert h.factory_calls == 1
    assert len(h.vector_store.query_calls) == 1  # corpus loaded once


# MKC-TC-S4-7-036 (negative): different resource_ids -> cache miss, re-index.
def test_bm25_cache_miss_on_different_resource_scope() -> None:
    h = _Harness(
        bm25_results=[_sr("c1")],
        vector_store=_FakeVectorStore(
            search_results=[_vsr("c2")],
            query_results=[_vsr("c1")],
        ),
    )

    h.service.retrieve(_request(resource_ids=["res-1"]))
    # Different scope (still authorized for res-1) -> different cache key -> miss.
    h.service.retrieve(_request(resource_ids=["res-1", "res-2"]))

    assert h.factory_calls == 2
    assert len(h.vector_store.query_calls) == 2


# MKC-TC-S4-7-017: unauthorized chunk (wrong user) -> 403 RetrievalForbiddenError.
def test_unauthorized_chunk_raises_forbidden() -> None:
    h = _Harness(
        bm25_results=[],
        vector_store=_FakeVectorStore(
            search_results=[_vsr("c1", user_id="intruder")],
        ),
    )

    with pytest.raises(RetrievalForbiddenError):
        h.service.retrieve(_request())


# MKC-TC-S4-7-037: timeout fallback to vector still validates authorization.
def test_timeout_fallback_vector_validates_authorization() -> None:
    clock = _ScriptedClock([0.0, 1000.0, 1000.0])
    h = _Harness(
        bm25_results=[],
        vector_store=_FakeVectorStore(
            search_results=[_vsr("c1", user_id="intruder")],
        ),
        config=_config(timeout_ms=800, fallback_to_vector=True),
        clock=clock,
    )

    with pytest.raises(RetrievalForbiddenError):
        h.service.retrieve(_request())


# MKC-TC-S4-7-038: timeout fallback to vector still applies score_threshold.
def test_timeout_fallback_vector_respects_score_threshold() -> None:
    clock = _ScriptedClock([0.0, 1000.0, 1000.0])
    h = _Harness(
        bm25_results=[],
        vector_store=_FakeVectorStore(
            search_results=[_vsr("c1", score=0.9), _vsr("c2", score=0.3)],
        ),
        config=_config(timeout_ms=800, fallback_to_vector=True, score_threshold=0.5),
        clock=clock,
    )

    result = h.service.retrieve(_request())

    assert result.degraded is True
    assert {c.chunk_id for c in result.chunks} == {"c1"}


# MKC-TC-S4-7-039: BM25 cache evicts oldest entries when max_entries exceeded.
def test_bm25_cache_evicts_lru_when_max_entries_exceeded() -> None:
    h = _Harness(
        bm25_results=[],
        vector_store=_FakeVectorStore(
            search_results=[],
            query_results=[_vsr("c1")],
        ),
        config=_config(bm25_cache_max_entries=2),
    )

    h.service.retrieve(_request(resource_ids=["res-1"]))
    h.service.retrieve(_request(resource_ids=["res-2"]))
    h.service.retrieve(_request(resource_ids=["res-3"]))

    cache_keys = list(h.service._bm25_cache.keys())
    assert len(cache_keys) == 2
    resources = {key.split("|")[1] for key in cache_keys}
    assert resources == {"res-2", "res-3"}
    assert h.factory_calls == 3

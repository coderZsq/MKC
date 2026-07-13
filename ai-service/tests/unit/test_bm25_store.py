from __future__ import annotations

import pytest

from app.models.hybrid_retrieval import SearchResult
from app.services.hybrid_retrieval.bm25_store import BM25Store


def _doc(
    chunk_id: str,
    text: str,
    resource_id: str = "res-1",
    user_id: str = "user-1",
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        resource_id=resource_id,
        user_id=user_id,
        text=text,
        score=0.0,
        source="bm25",
        metadata={},
    )


# MKC-TC-S4-7-002: BM25 returns Top-K with source=bm25 and positive scores.
def test_bm25_returns_top_k_with_bm25_source() -> None:
    store = BM25Store(tokenizer="whitespace")
    store.index(
        [
            _doc("c1", "quick brown fox"),
            _doc("c2", "lazy dog sleeps"),
            _doc("c3", "quick fox runs fast"),
        ],
    )

    hits = store.search("quick fox", top_k=5)

    chunk_ids = {hit.chunk_id for hit in hits}
    assert chunk_ids == {"c1", "c3"}
    assert all(hit.source == "bm25" for hit in hits)
    assert all(hit.score > 0 for hit in hits)


def test_bm25_top_k_truncation() -> None:
    # N=5 with the query term in 3 docs keeps BM25 IDF positive (term in < N/2
    # docs); the 3 matches are then truncated to ``top_k``.
    store = BM25Store(tokenizer="whitespace")
    store.index(
        [
            _doc("c1", "alpha beta"),
            _doc("c2", "alpha gamma"),
            _doc("c3", "alpha delta"),
            _doc("c4", "epsilon"),
            _doc("c5", "zeta"),
        ],
    )

    hits = store.search("alpha", top_k=2)
    assert len(hits) == 2


def test_bm25_empty_corpus_returns_empty() -> None:
    store = BM25Store(tokenizer="whitespace")
    store.index([])
    assert store.search("anything", top_k=5) == []


def test_bm25_no_token_overlap_returns_empty() -> None:
    store = BM25Store(tokenizer="whitespace")
    store.index([_doc("c1", "alpha beta")])
    assert store.search("zeta", top_k=5) == []


# MKC-TC-S4-7-015: BM25 enforces user_id filter.
def test_bm25_user_id_filter() -> None:
    # c2 matches the query with a positive score but is filtered out by user_id;
    # the filler docs keep IDF positive (term in 2 of 5 docs).
    store = BM25Store(tokenizer="whitespace")
    store.index(
        [
            _doc("c1", "apple", user_id="user-1"),
            _doc("c2", "apple", user_id="user-2"),
            _doc("c3", "banana", user_id="user-1"),
            _doc("c4", "cherry", user_id="user-1"),
            _doc("c5", "date", user_id="user-1"),
        ],
    )

    hits = store.search("apple", top_k=5, filters={"user_id": "user-1"})
    assert {hit.chunk_id for hit in hits} == {"c1"}


# MKC-TC-S4-7-016: BM25 enforces resource_ids filter.
def test_bm25_resource_ids_filter() -> None:
    # c1 matches the query with a positive score but is filtered out by
    # resource_ids; filler docs keep IDF positive (term in 2 of 5 docs).
    store = BM25Store(tokenizer="whitespace")
    store.index(
        [
            _doc("c1", "apple", resource_id="res-1"),
            _doc("c2", "apple", resource_id="res-2"),
            _doc("c3", "banana", resource_id="res-1"),
            _doc("c4", "cherry", resource_id="res-1"),
            _doc("c5", "date", resource_id="res-1"),
        ],
    )

    hits = store.search("apple", top_k=5, filters={"resource_ids": ["res-2"]})
    assert {hit.chunk_id for hit in hits} == {"c2"}


def test_bm25_invalid_tokenizer_raises() -> None:
    with pytest.raises(ValueError):
        BM25Store(tokenizer="unknown")


# MKC-TC-S4-7-011: jieba tokenizes Chinese text for BM25 retrieval.
def test_bm25_jieba_chinese_tokenization() -> None:
    jieba = pytest.importorskip("jieba")  # noqa: F841
    # N=5 keeps the shared query term ("会议") in 2 of 5 docs so its BM25 IDF is
    # positive without relying on the epsilon floor; "讨论" appears only in c1.
    store = BM25Store(tokenizer="jieba")
    store.index(
        [
            _doc("c1", "本次会议讨论了产品路线图"),
            _doc("c2", "这次会议非常重要"),
            _doc("c3", "天气晴朗适合户外活动"),
            _doc("c4", "项目计划包含多个里程碑"),
            _doc("c5", "团队协作与沟通机制"),
        ],
    )

    hits = store.search("会议讨论", top_k=5)
    chunk_ids = [hit.chunk_id for hit in hits]
    # Both meeting-related docs match; the unrelated docs do not.
    assert "c1" in chunk_ids
    assert "c2" in chunk_ids
    assert "c3" not in chunk_ids
    assert hits[0].chunk_id == "c1"

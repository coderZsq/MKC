from __future__ import annotations

from app.models.hybrid_retrieval import SearchResult
from app.services.hybrid_retrieval.rrf import reciprocal_rank_fusion


def _hit(chunk_id: str, source: str = "bm25", resource_id: str = "res-1") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        resource_id=resource_id,
        user_id="user-1",
        text=f"text-{chunk_id}",
        score=0.0,
        source=source,  # type: ignore[arg-type]
        metadata={},
    )


# MKC-TC-S4-7-004: RRF deduplicates by chunk_id and sorts by fused score desc.
def test_rrf_deduplicates_by_chunk_id_and_sorts_desc() -> None:
    # bm25: a(0), b(1), c(2) ; vector: a(0), c(1), d(2)
    # fused: a=2/61, c=1/63+1/62, b=1/62, d=1/63  -> distinct, strict order.
    bm25_hits = [_hit("a"), _hit("b"), _hit("c")]
    vector_hits = [
        _hit("a", source="vector"),
        _hit("c", source="vector"),
        _hit("d", source="vector"),
    ]

    fused = reciprocal_rank_fusion(bm25_hits, vector_hits, k=60)

    chunk_ids = [hit.chunk_id for hit in fused]
    assert chunk_ids == ["a", "c", "b", "d"]
    # No duplicate chunk_ids.
    assert len(chunk_ids) == len(set(chunk_ids))
    # Scores strictly descending.
    scores = [hit.score for hit in fused]
    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_rrf_combined_score_beats_single_path() -> None:
    bm25_hits = [_hit("a"), _hit("b")]
    vector_hits = [_hit("a", source="vector"), _hit("b", source="vector")]

    fused = reciprocal_rank_fusion(bm25_hits, vector_hits, k=60)

    # "a" appears at rank 1 in both paths -> highest fused score.
    assert fused[0].chunk_id == "a"
    expected = 1.0 / (60 + 1) + 1.0 / (60 + 1)
    assert fused[0].score == expected


# MKC-TC-S4-7-007: bm25_weight / vector_weight are configurable.
def test_rrf_weights_bias_toward_heavier_path() -> None:
    bm25_hits = [_hit("a"), _hit("b")]
    vector_hits = [_hit("b", source="vector"), _hit("a", source="vector")]

    # Heavily weight vector path: vector rank-1 ("b") should win overall.
    fused = reciprocal_rank_fusion(
        bm25_hits,
        vector_hits,
        bm25_weight=0.0,
        vector_weight=1.0,
        k=60,
    )

    assert fused[0].chunk_id == "b"


def test_rrf_preserves_first_seen_source() -> None:
    bm25_hits = [_hit("a", source="bm25")]
    vector_hits = [_hit("a", source="vector")]

    fused = reciprocal_rank_fusion(bm25_hits, vector_hits, k=60)

    assert fused[0].source == "bm25"


def test_rrf_empty_inputs_returns_empty() -> None:
    assert reciprocal_rank_fusion([], [], k=60) == []


def test_rrf_single_path_only() -> None:
    bm25_hits = [_hit("a"), _hit("b"), _hit("c")]
    fused = reciprocal_rank_fusion(bm25_hits, [], k=60)
    assert [hit.chunk_id for hit in fused] == ["a", "b", "c"]


def test_rrf_k_smoothing_affects_scores() -> None:
    bm25_hits = [_hit("a"), _hit("b")]
    vector_hits = [_hit("a", source="vector"), _hit("b", source="vector")]

    small_k = reciprocal_rank_fusion(bm25_hits, vector_hits, k=1)
    large_k = reciprocal_rank_fusion(bm25_hits, vector_hits, k=1000)

    # Smaller k => larger absolute fused scores.
    assert small_k[0].score > large_k[0].score

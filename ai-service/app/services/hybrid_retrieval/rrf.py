from __future__ import annotations

from app.models.hybrid_retrieval import SearchResult


def reciprocal_rank_fusion(
    bm25_hits: list[SearchResult],
    vector_hits: list[SearchResult],
    bm25_weight: float = 1.0,
    vector_weight: float = 1.0,
    k: int = 60,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion: merge two ranked lists, deduplicating by chunk_id.

    The fused score for a chunk is::

        score = w_bm25 / (k + rank_bm25 + 1) + w_vector / (k + rank_vector + 1)

    where ranks are 0-indexed. The first-seen ``SearchResult`` is kept as the
    carrier (its ``source`` is preserved), with only ``score`` updated to the
    fused value. Results are returned sorted by fused score descending.
    """
    scores: dict[str, float] = {}
    meta: dict[str, SearchResult] = {}

    for rank, hit in enumerate(bm25_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + bm25_weight / (k + rank + 1)
        meta.setdefault(hit.chunk_id, hit)

    for rank, hit in enumerate(vector_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + vector_weight / (k + rank + 1)
        meta.setdefault(hit.chunk_id, hit)

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        meta[cid].model_copy(update={"score": float(score), "metadata": dict(meta[cid].metadata)})
        for cid, score in ordered
    ]

from __future__ import annotations

from app.models.hybrid_retrieval import SearchResult
from app.services.hybrid_retrieval.reranker import Reranker


class _FakeModel:
    """Mimics ``CrossEncoder.predict`` without loading weights."""

    def __init__(self, scores: list[float]) -> None:
        self._scores = scores
        self.calls: int = 0

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        self.calls += 1
        assert len(pairs) == len(self._scores)
        return list(self._scores)


def _candidate(chunk_id: str, text: str, score: float = 0.0) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        resource_id="res-1",
        user_id="user-1",
        text=text,
        score=score,
        source="vector",
        metadata={},
    )


# MKC-TC-S4-7-005: Reranker reorders candidates by cross-encoder score.
def test_reranker_reorders_by_score_and_tags_source() -> None:
    model = _FakeModel(scores=[0.1, 0.9, 0.5])
    reranker = Reranker(enabled=True, model=model)
    candidates = [
        _candidate("c1", "alpha", score=5.0),
        _candidate("c2", "beta", score=1.0),
        _candidate("c3", "gamma", score=3.0),
    ]

    ranked = reranker.rerank("query", candidates, top_n=3)

    assert [c.chunk_id for c in ranked] == ["c2", "c3", "c1"]
    assert [c.score for c in ranked] == [0.9, 0.5, 0.1]
    assert all(c.source == "rerank" for c in ranked)
    assert model.calls == 1


# MKC-TC-S4-7-008: Disabled reranker returns candidates truncated to top_n unchanged.
def test_reranker_disabled_returns_candidates_unchanged() -> None:
    model = _FakeModel(scores=[])
    reranker = Reranker(enabled=False, model=model)
    candidates = [
        _candidate("c1", "alpha", score=0.8),
        _candidate("c2", "beta", score=0.5),
        _candidate("c3", "gamma", score=0.3),
    ]

    ranked = reranker.rerank("query", candidates, top_n=2)

    assert [c.chunk_id for c in ranked] == ["c1", "c2"]
    # Source/score preserved (no reranking applied).
    assert all(c.source == "vector" for c in ranked)
    assert [c.score for c in ranked] == [0.8, 0.5]
    assert model.calls == 0  # model never invoked when disabled


def test_reranker_empty_candidates_returns_empty() -> None:
    reranker = Reranker(enabled=True, model=_FakeModel(scores=[]))
    assert reranker.rerank("query", [], top_n=5) == []


def test_reranker_top_n_truncation() -> None:
    model = _FakeModel(scores=[0.3, 0.9, 0.5])
    reranker = Reranker(enabled=True, model=model)
    candidates = [
        _candidate("c1", "alpha"),
        _candidate("c2", "beta"),
        _candidate("c3", "gamma"),
    ]

    ranked = reranker.rerank("query", candidates, top_n=1)
    assert [c.chunk_id for c in ranked] == ["c2"]


def test_reranker_enabled_property() -> None:
    assert Reranker(enabled=True).enabled is True
    assert Reranker(enabled=False).enabled is False

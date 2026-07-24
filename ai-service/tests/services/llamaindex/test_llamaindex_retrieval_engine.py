from __future__ import annotations

from typing import Any

import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from app.core.exceptions import (
    LlamaIndexRetrievalForbiddenError,
    RetrievalUnavailableError,
)
from app.models.retrieval import RetrievalRequest
from app.services.chunking.token_estimator import TokenEstimator
from app.services.llamaindex.context_compressor import LlamaIndexContextCompressor
from app.services.llamaindex.retrieval_engine import (
    LlamaIndexRetrievalConfig,
    LlamaIndexRetrievalEngine,
)
from app.services.retrieval.prompt_builder import PromptBuilder


class _FakeRetriever:
    def __init__(self, results: list[TextNode | NodeWithScore] | None = None) -> None:
        self.results = results or []
        self.calls: list[dict[str, Any]] = []

    def query(
        self,
        query: str,
        *,
        user_id: str,
        resource_ids: list[str],
        top_k: int = 10,
    ) -> list[TextNode | NodeWithScore]:
        self.calls.append(
            {
                "query": query,
                "user_id": user_id,
                "resource_ids": resource_ids,
                "top_k": top_k,
            }
        )
        return self.results


class _PerResourceRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def query(
        self,
        query: str,
        *,
        user_id: str,
        resource_ids: list[str],
        top_k: int = 10,
    ) -> list[TextNode | NodeWithScore]:
        self.calls.append(
            {
                "query": query,
                "user_id": user_id,
                "resource_ids": resource_ids,
                "top_k": top_k,
            }
        )
        if resource_ids == ["audio-res"]:
            return [_node("audio-1", "audio-res", "user-1", "audio insight", score=0.82)]
        if len(resource_ids) == 1:
            return []
        return [
            _node(f"pdf-{index}", f"pdf-res-{index}", "user-1", "duplicate text", score=0.95)
            for index in range(4)
        ]


class _FailingRetriever:
    def query(
        self,
        query: str,
        *,
        user_id: str,
        resource_ids: list[str],
        top_k: int = 10,
    ) -> list[TextNode | NodeWithScore]:
        raise RuntimeError("llamaindex down")


def _node(
    chunk_id: str,
    resource_id: str,
    user_id: str,
    text: str,
    *,
    score: float | None = None,
) -> TextNode:
    metadata: dict[str, Any] = {
        "chunk_id": chunk_id,
        "resource_id": resource_id,
        "user_id": user_id,
    }
    if score is not None:
        metadata["score"] = score
    return TextNode(id_=chunk_id, text=text, metadata=metadata)


def _node_with_score(
    chunk_id: str,
    resource_id: str,
    user_id: str,
    text: str,
    *,
    score: float | None,
) -> NodeWithScore:
    return NodeWithScore(node=_node(chunk_id, resource_id, user_id, text), score=score)


def _engine(
    retriever: object,
    *,
    config: LlamaIndexRetrievalConfig | None = None,
    prompt_builder: PromptBuilder | None = None,
) -> LlamaIndexRetrievalEngine:
    return LlamaIndexRetrievalEngine(
        retriever=retriever,  # type: ignore[arg-type]
        prompt_builder=prompt_builder
        or PromptBuilder(template_text="chunks:{{ chunks|length }} question:{{ question }}"),
        config=config,
        context_compressor=LlamaIndexContextCompressor(TokenEstimator()),
    )


def _request(**overrides: Any) -> RetrievalRequest:
    data: dict[str, Any] = {
        "question": "what is relevant?",
        "user_id": "user-1",
        "resource_ids": ["res-1"],
    }
    data.update(overrides)
    return RetrievalRequest(**data)


def test_retrieve_accepts_retrieval_request_and_returns_result() -> None:
    retriever = _FakeRetriever([_node("c-1", "res-1", "user-1", "relevant", score=0.9)])

    result = _engine(retriever).retrieve(_request())

    assert result.chunks[0].chunk_id == "c-1"
    assert result.chunks[0].resource_id == "res-1"
    assert result.chunks[0].score == 0.9
    assert result.prompt == "chunks:1 question:what is relevant?"
    assert result.context_token_count > 0
    assert retriever.calls == [
        {
            "query": "what is relevant?",
            "user_id": "user-1",
            "resource_ids": ["res-1"],
            "top_k": 5,
        }
    ]


def test_retrieve_honors_top_k() -> None:
    retriever = _FakeRetriever(
        [
            _node(f"c-{index}", "res-1", "user-1", f"text {index}", score=0.95 - index * 0.01)
            for index in range(5)
        ]
    )

    result = _engine(retriever).retrieve(_request(top_k=3, score_threshold=0.0))

    assert len(result.chunks) == 3
    assert retriever.calls[0]["top_k"] == 3


def test_retrieve_honors_score_threshold() -> None:
    retriever = _FakeRetriever(
        [
            _node("high", "res-1", "user-1", "high", score=0.91),
            _node("low", "res-1", "user-1", "low", score=0.42),
        ]
    )

    result = _engine(retriever).retrieve(_request(score_threshold=0.8))

    assert [chunk.chunk_id for chunk in result.chunks] == ["high"]


def test_retrieve_honors_max_context_tokens() -> None:
    retriever = _FakeRetriever(
        [
            _node("long", "res-1", "user-1", "word " * 1000, score=0.95),
            _node("short", "res-1", "user-1", "second chunk", score=0.9),
        ]
    )

    result = _engine(retriever).retrieve(_request(max_context_tokens=20, score_threshold=0.0))

    assert [chunk.chunk_id for chunk in result.chunks] == ["long"]
    assert result.context_token_count > 20


def test_retrieve_attempts_per_resource_candidates() -> None:
    retriever = _PerResourceRetriever()

    result = _engine(retriever).retrieve(
        _request(
            resource_ids=[
                "pdf-res-0",
                "pdf-res-1",
                "pdf-res-2",
                "pdf-res-3",
                "audio-res",
            ],
            top_k=5,
            score_threshold=0.7,
        )
    )

    assert [chunk.chunk_id for chunk in result.chunks] == ["pdf-0", "audio-1"]
    assert retriever.calls[0]["top_k"] > 5
    assert retriever.calls[-1]["resource_ids"] == ["audio-res"]
    assert len(retriever.calls) == 6


def test_retrieve_rejects_unauthorized_resource() -> None:
    retriever = _FakeRetriever([_node("c-1", "other-res", "user-1", "text", score=0.9)])

    with pytest.raises(LlamaIndexRetrievalForbiddenError) as exc_info:
        _engine(retriever).retrieve(_request(resource_ids=["res-1"]))

    assert exc_info.value.code == "RETRIEVAL_FORBIDDEN"
    assert exc_info.value.status_code == 403


def test_retrieve_rejects_unauthorized_user() -> None:
    retriever = _FakeRetriever([_node("c-1", "res-1", "other-user", "text", score=0.9)])

    with pytest.raises(LlamaIndexRetrievalForbiddenError) as exc_info:
        _engine(retriever).retrieve(_request())

    assert exc_info.value.code == "RETRIEVAL_FORBIDDEN"


def test_retrieve_empty_results_returns_explainable_prompt() -> None:
    result = _engine(_FakeRetriever(), prompt_builder=PromptBuilder()).retrieve(_request())

    assert result.chunks == []
    assert "无相关知识" in result.prompt
    assert result.context_token_count == 0


def test_retrieve_maps_retriever_errors() -> None:
    with pytest.raises(RetrievalUnavailableError) as exc_info:
        _engine(_FailingRetriever()).retrieve(_request())

    assert exc_info.value.code == "RETRIEVAL_UNAVAILABLE"
    assert exc_info.value.status_code == 503


def test_retrieve_defaults_missing_score_to_zero_without_crashing() -> None:
    retriever = _FakeRetriever([_node_with_score("c-1", "res-1", "user-1", "text", score=None)])

    result = _engine(retriever).retrieve(_request(score_threshold=0.0))

    assert result.chunks[0].score == 0.0

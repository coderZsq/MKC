from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.agent.nodes import AgentNodes
from app.agent.runner import AgentConfig
from app.agent.state import REQUIRED_AGENT_STATE_FIELDS
from app.core.exceptions import RetrievalForbiddenError, RetrievalUnavailableError
from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.llm.models import LLMResponse, LLMStreamChunk, Usage


def _run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


async def _stream(chunks: list[str]) -> AsyncIterator[LLMStreamChunk]:
    for chunk in chunks:
        yield LLMStreamChunk(delta=chunk)
    yield LLMStreamChunk(delta="", finish_reason="stop")


def _nodes() -> tuple[AgentNodes, MagicMock, MagicMock]:
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        chunks=[
            RetrievalChunk(
                chunk_id="c-1",
                resource_id="res-1",
                text="resource text",
                score=0.9,
                metadata={"page": 1},
            )
        ],
        prompt="prompt",
        context_token_count=2,
    )
    llm = MagicMock()
    llm.stream_complete.side_effect = lambda _request: _stream(["hello", " world"])
    llm.complete.return_value = LLMResponse(
        content="compare",
        model="mock",
        finish_reason="stop",
        usage=Usage(),
    )
    return AgentNodes(retrieval, llm, config=AgentConfig()), retrieval, llm


def test_agent_state_required_fields_are_declared() -> None:
    assert {
        "messages",
        "intent",
        "retrieved_chunks",
        "draft_answer",
        "citations",
        "iterations",
    } == REQUIRED_AGENT_STATE_FIELDS


def test_intent_node_fixed_and_dynamic_paths() -> None:
    nodes, _, llm = _nodes()
    fixed = _run(nodes.intent_node({"question": "请总结资料", "intent": ""}))
    assert fixed == {"intent": "summarize"}

    dynamic_nodes = AgentNodes(MagicMock(), llm, config=AgentConfig(enable_dynamic_intent=True))
    dynamic = _run(dynamic_nodes.intent_node({"question": "anything", "intent": ""}))
    assert dynamic == {"intent": "compare"}
    llm.complete.assert_called_once()


def test_retrieval_node_maps_chunks_without_prebuilt_citations() -> None:
    nodes, retrieval, _ = _nodes()
    update = _run(
        nodes.retrieval_node(
            {
                "question": "q",
                "user_id": "u",
                "resource_ids": ["res-1"],
                "top_k": 3,
                "score_threshold": 0.5,
            }
        )
    )
    assert len(update["retrieved_chunks"]) == 1
    assert update["citations"] == []
    retrieval.retrieve.assert_called_once()


def test_retrieval_failure_degrades_to_empty_context() -> None:
    nodes, retrieval, _ = _nodes()
    retrieval.retrieve.side_effect = RetrievalUnavailableError()
    update = _run(
        nodes.retrieval_node({"question": "q", "user_id": "u", "resource_ids": ["res-1"]})
    )
    assert update == {"retrieved_chunks": [], "citations": []}


def test_retrieval_forbidden_is_not_swallowed() -> None:
    nodes, retrieval, _ = _nodes()
    retrieval.retrieve.side_effect = RetrievalForbiddenError()
    with pytest.raises(RetrievalForbiddenError):
        _run(nodes.retrieval_node({"question": "q", "user_id": "u", "resource_ids": ["res-2"]}))


def test_qa_generate_and_validate_nodes() -> None:
    nodes, _, llm = _nodes()
    state = {
        "question": "q",
        "retrieved_chunks": [
            RetrievalChunk(
                chunk_id="c-1",
                resource_id="res-1",
                text="text",
                score=0.9,
                metadata={},
            )
        ],
        "citations": [{"resource_id": "res-1"}],
        "iterations": 0,
    }
    update = _run(nodes.qa_node(state))
    assert update["draft_answer"] == "hello world"
    assert llm.stream_complete.called
    passed_request = llm.stream_complete.call_args.args[0]
    assert passed_request.messages[-1].role == "user"
    assert "[^1] resource=res-1" in passed_request.messages[-1].content

    state.update(update)
    validate = _run(nodes.validate_node(state))
    assert validate["validation_passed"] is True
    assert validate["iterations"] == 1


def test_validate_marks_low_confidence_at_limit() -> None:
    nodes, _, _ = _nodes()
    update = _run(
        nodes.validate_node(
            {
                "draft_answer": "answer",
                "retrieved_chunks": [],
                "citations": [{"resource_id": "missing"}],
                "iterations": 2,
            }
        )
    )
    assert update["validation_passed"] is True
    assert update["low_confidence"] is True


@pytest.mark.parametrize("node_name", ["compare", "generate"])
def test_stream_generation_for_branches(node_name: str) -> None:
    nodes, _, _ = _nodes()

    async def collect() -> list[str]:
        return [
            delta
            async for delta in nodes.stream_generation(
                {"question": "q", "retrieved_chunks": []}, node_name
            )
        ]

    assert asyncio.run(collect()) == [LLMStreamChunk(delta="hello"), LLMStreamChunk(delta=" world")]

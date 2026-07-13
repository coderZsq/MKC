from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.agent.nodes import AgentNodes
from app.agent.runner import AgentConfig
from app.models.qa import ChatMessage
from app.models.retrieval import RetrievalChunk
from app.services.llm.models import LLMStreamChunk


def _run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


async def _stream(chunks: list[str]) -> AsyncIterator[LLMStreamChunk]:
    for chunk in chunks:
        yield LLMStreamChunk(delta=chunk)
    yield LLMStreamChunk(delta="", finish_reason="stop")


def _nodes() -> AgentNodes:
    retrieval = MagicMock()
    llm = MagicMock()
    llm.stream_complete.side_effect = lambda _request: _stream(["hello"])
    return AgentNodes(retrieval, llm, config=AgentConfig())


@pytest.mark.parametrize("node_name", ["qa", "compare", "generate"])
def test_history_messages_are_included(node_name: str) -> None:
    nodes = _nodes()
    state = {
        "question": "q",
        "retrieved_chunks": [],
        "messages": [
            ChatMessage(role="user", content=" earlier "),
            ChatMessage(role="assistant", content=" earlier answer "),
        ],
    }
    _run(getattr(nodes, f"{node_name}_node")(state))
    passed_request = nodes._llm.stream_complete.call_args.args[0]
    roles = [m.role for m in passed_request.messages]
    assert "user" in roles
    assert "assistant" in roles
    history_user = next(
        m for m in passed_request.messages if m.role == "user" and m.content == " earlier "
    )
    assert history_user is not None


def test_memory_context_appears_as_system_message() -> None:
    nodes = _nodes()
    state = {
        "question": "q",
        "retrieved_chunks": [],
        "memory_context": "长期记忆：用户叫 Alice",
    }
    _run(nodes.qa_node(state))
    passed_request = nodes._llm.stream_complete.call_args.args[0]
    assert passed_request.messages[0].role == "system"
    assert "用户叫 Alice" in passed_request.messages[0].content
    assert "引用上下文片段" in passed_request.messages[0].content


def test_citation_rules_not_in_user_prompt() -> None:
    nodes = _nodes()
    chunk = RetrievalChunk(chunk_id="c-1", resource_id="res-1", text="text", score=0.9, metadata={})
    state = {"question": "q", "retrieved_chunks": [chunk], "memory_context": ""}
    _run(nodes.qa_node(state))
    passed_request = nodes._llm.stream_complete.call_args.args[0]
    user_message = passed_request.messages[-1]
    assert user_message.role == "user"
    assert "引用上下文片段" not in user_message.content
    assert "[^1] resource=res-1" in user_message.content


def test_generate_node_includes_memory_context_but_no_citation_rules() -> None:
    nodes = _nodes()
    state = {
        "question": "hello",
        "retrieved_chunks": [],
        "memory_context": "memory snippet",
    }
    _run(nodes.generate_node(state))
    passed_request = nodes._llm.stream_complete.call_args.args[0]
    assert passed_request.messages[0].role == "system"
    assert "memory snippet" in passed_request.messages[0].content
    assert "引用上下文片段" not in passed_request.messages[0].content


def test_generate_node_without_memory_has_single_user_message() -> None:
    nodes = _nodes()
    state = {"question": "hello", "retrieved_chunks": []}
    _run(nodes.generate_node(state))
    passed_request = nodes._llm.stream_complete.call_args.args[0]
    assert len(passed_request.messages) == 1
    assert passed_request.messages[0].role == "user"
    assert passed_request.messages[0].content == "hello"


def test_stream_generation_passes_history() -> None:
    nodes = _nodes()
    state = {
        "question": "q",
        "retrieved_chunks": [],
        "messages": [ChatMessage(role="user", content="hi")],
    }

    async def collect() -> list[LLMStreamChunk]:
        return [chunk async for chunk in nodes.stream_generation(state, "compare")]

    assert asyncio.run(collect()) == [LLMStreamChunk(delta="hello")]
    passed_request = nodes._llm.stream_complete.call_args.args[0]
    assert any(m.role == "user" and m.content == "hi" for m in passed_request.messages)

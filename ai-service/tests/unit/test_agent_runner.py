from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

from app.agent import AgentConfig, AgentGraph, AgentNodes, AgentRunner
from app.agent.checkpointer import AgentCheckpointer
from app.models.agent import AgentRunRequest
from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.citation_formatter import CitationFormatter
from app.services.citation_service import CitationService
from app.services.citation_validator import CitationValidator
from app.services.llm.models import LLMStreamChunk


async def _stream(_request: object) -> AsyncIterator[LLMStreamChunk]:
    yield LLMStreamChunk(delta="agent [^1]")
    yield LLMStreamChunk(delta=" answer")
    yield LLMStreamChunk(delta="", finish_reason="stop")


def test_runner_streams_node_chunk_citation_done_events() -> None:
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        chunks=[
            RetrievalChunk(
                chunk_id="c-1",
                resource_id="res-1",
                text="text",
                score=0.9,
                metadata={"page": 1},
            )
        ],
        prompt="prompt",
        context_token_count=1,
    )
    llm = MagicMock()
    llm.stream_complete.side_effect = _stream
    checkpointer = AgentCheckpointer()
    nodes = AgentNodes(retrieval, llm, config=AgentConfig())
    runner = AgentRunner(
        AgentGraph(nodes, checkpointer),
        AgentConfig(),
        checkpointer,
        citation_service=CitationService(CitationFormatter(), CitationValidator(log_dropped=False)),
    )

    async def collect() -> list[str]:
        events = [
            event
            async for event in runner.run_stream(
                AgentRunRequest(
                    question="what?",
                    conversation_id="conv-1",
                    message_id="msg-1",
                    user_id="user-1",
                    resource_ids=["res-1"],
                )
            )
        ]
        assert next(event for event in events if event.event_type == "citation").data == {
            "message_id": "msg-1",
            "index": 1,
            "chunk_id": "c-1",
            "resource_id": "res-1",
            "resource_type": "pdf",
            "page": 1,
            "score": 0.9,
            "snippet": "text",
        }
        assert events[-1].data["citation_count"] == 1
        return [event.event_type for event in events]

    event_types = asyncio.run(collect())
    assert event_types[:4] == ["node_start", "node_end", "node_start", "node_end"]
    assert "chunk" in event_types
    assert "citation" in event_types
    assert event_types[-1] == "done"
    assert checkpointer.load("conv-1") is not None

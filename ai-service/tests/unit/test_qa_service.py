from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import RetrievalUnavailableError
from app.models.qa import ChatMessage, QARequest, QAStreamEvent, format_sse_event
from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMStreamChunk
from app.services.qa_service import QAService
from app.services.retrieval.retrieval_service import RetrievalService


def _collect_events(stream: AsyncIterator[QAStreamEvent]) -> list[QAStreamEvent]:
    return asyncio.run(_consume(stream))


async def _consume(stream: AsyncIterator[QAStreamEvent]) -> list[QAStreamEvent]:
    return [event async for event in stream]


@pytest.fixture
def qa_request() -> QARequest:
    return QARequest(
        question="What is the answer?",
        conversation_id="conv-1",
        message_id="msg-1",
        user_id="user-1",
        resource_ids=["res-1"],
    )


def test_stream_answer_emits_chunk_citation_done(qa_request: QARequest) -> None:
    retrieval_result = RetrievalResult(
        chunks=[
            RetrievalChunk(
                chunk_id="chunk-1",
                resource_id="res-1",
                text="relevant text",
                score=0.95,
                metadata={"page": 1},
            ),
        ],
        prompt="constructed prompt",
        context_token_count=10,
    )
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.return_value = retrieval_result

    llm_client = MagicMock(spec=LLMClient)

    async def _fake_stream(_request: object) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(delta="hello")
        yield LLMStreamChunk(delta=" ")
        yield LLMStreamChunk(delta="world", finish_reason="stop")

    llm_client.stream_complete.side_effect = _fake_stream

    service = QAService(retrieval_service, llm_client)
    events = _collect_events(service.stream_answer(qa_request))

    assert [e.event_type for e in events] == ["chunk", "chunk", "chunk", "citation", "done"]
    assert events[0].data["delta"] == "hello"
    assert events[0].data["index"] == 0
    assert events[3].data["resource_id"] == "res-1"
    assert events[3].data["score"] == 0.95
    assert events[4].data["finish_reason"] == "stop"

    retrieval_service.retrieve.assert_called_once()
    llm_client.stream_complete.assert_called_once()


def test_stream_answer_includes_history(qa_request: QARequest) -> None:
    qa_request.history = [
        ChatMessage(role="user", content="previous question"),
        ChatMessage(role="assistant", content="previous answer"),
    ]

    retrieval_result = RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.return_value = retrieval_result

    llm_client = MagicMock(spec=LLMClient)

    async def _fake_stream(_request: object) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(delta="ok", finish_reason="stop")

    llm_client.stream_complete.side_effect = _fake_stream

    service = QAService(retrieval_service, llm_client)
    _collect_events(service.stream_answer(qa_request))

    passed_request = llm_client.stream_complete.call_args[0][0]
    assert len(passed_request.messages) == 3
    assert passed_request.messages[0].role == "user"
    assert passed_request.messages[0].content == "previous question"
    assert passed_request.messages[1].role == "assistant"
    assert passed_request.messages[2].role == "user"


def test_stream_answer_retrieval_error_yields_error_event(qa_request: QARequest) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.side_effect = RetrievalUnavailableError()

    llm_client = MagicMock(spec=LLMClient)
    service = QAService(retrieval_service, llm_client)

    events = _collect_events(service.stream_answer(qa_request))

    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].data["error_code"] == "RETRIEVAL_UNAVAILABLE"
    llm_client.stream_complete.assert_not_called()


def test_stream_answer_llm_error_yields_error_event(qa_request: QARequest) -> None:
    retrieval_result = RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.return_value = retrieval_result

    llm_client = MagicMock(spec=LLMClient)

    async def _fake_stream(_request: object) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(delta="partial", finish_reason="error")

    llm_client.stream_complete.side_effect = _fake_stream

    service = QAService(retrieval_service, llm_client)
    events = _collect_events(service.stream_answer(qa_request))

    assert events[-1].event_type == "error"
    assert events[-1].data["error_code"] == "LLM_TIMEOUT"


def test_stream_answer_generic_exception_yields_error_event(qa_request: QARequest) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.side_effect = RuntimeError("boom")

    llm_client = MagicMock(spec=LLMClient)
    service = QAService(retrieval_service, llm_client)

    events = _collect_events(service.stream_answer(qa_request))

    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].data["error_code"] == "RETRIEVAL_UNAVAILABLE"


def test_format_sse_event_renders_valid_json() -> None:
    payload = format_sse_event("chunk", {"message_id": "msg-1", "delta": "hi"})
    assert payload.startswith("event: chunk\ndata: ")
    parsed = json.loads(payload.split("\ndata: ")[1])
    assert parsed["delta"] == "hi"

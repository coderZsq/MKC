from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from app.core.exceptions import LlamaIndexRetrievalForbiddenError, RetrievalUnavailableError
from app.models.qa import QARequest, QAStreamEvent
from app.models.retrieval import RetrievalChunk, RetrievalRequest, RetrievalResult
from app.services.citation_formatter import CitationFormatter
from app.services.citation_service import CitationService
from app.services.citation_validator import CitationValidator
from app.services.llm.models import LLMStreamChunk
from app.services.qa_service import QAService


class _FakeRagEngine:
    def __init__(
        self,
        result: RetrievalResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
        self.error = error
        self.requests: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


class _FakeLLMClient:
    def __init__(self, chunks: list[LLMStreamChunk]) -> None:
        self.chunks = chunks
        self.requests: list[object] = []

    async def stream_complete(self, request: object) -> AsyncIterator[LLMStreamChunk]:
        self.requests.append(request)
        for chunk in self.chunks:
            yield chunk


def _collect_events(stream: AsyncIterator[QAStreamEvent]) -> list[QAStreamEvent]:
    return asyncio.run(_consume(stream))


async def _consume(stream: AsyncIterator[QAStreamEvent]) -> list[QAStreamEvent]:
    return [event async for event in stream]


def _request(resource_ids: list[str] | None = None) -> QARequest:
    return QARequest(
        question="What is the answer?",
        conversation_id="conv-1",
        message_id="msg-1",
        user_id="user-1",
        resource_ids=["res-1"] if resource_ids is None else resource_ids,
    )


def _retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        chunks=[
            RetrievalChunk(
                chunk_id="chunk-1",
                resource_id="res-1",
                text="relevant text",
                score=0.95,
                metadata={"page": 2, "resource_type": "pdf", "user_id": "user-1"},
            )
        ],
        prompt="constructed prompt",
        context_token_count=10,
    )


@pytest.mark.parametrize("engine_name", ["legacy", "llamaindex"])
def test_stream_answer_emits_same_sse_types_for_both_engines(engine_name: str) -> None:
    rag_engine = _FakeRagEngine(_retrieval_result())
    llm_client = _FakeLLMClient(
        [
            LLMStreamChunk(delta="hello [^1]"),
            LLMStreamChunk(delta="", reasoning_delta="thinking"),
            LLMStreamChunk(delta=" world", finish_reason="stop"),
        ]
    )
    service = QAService(
        rag_engine,
        llm_client,  # type: ignore[arg-type]
        citation_service=CitationService(CitationFormatter(), CitationValidator(log_dropped=False)),
    )

    events = _collect_events(service.stream_answer(_request()))

    assert [event.event_type for event in events] == [
        "chunk",
        "reasoning",
        "chunk",
        "citation",
        "done",
    ]
    assert events[3].data["chunk_id"] == "chunk-1"
    assert events[3].data["resource_id"] == "res-1"
    assert events[3].data["resource_type"] == "pdf"
    assert events[3].data["page"] == 2
    assert events[-1].data["citation_count"] == 1
    assert rag_engine.requests[0].question == "What is the answer?"
    assert engine_name in {"legacy", "llamaindex"}


def test_stream_answer_without_resource_ids_skips_rag_engine() -> None:
    rag_engine = _FakeRagEngine(_retrieval_result())
    llm_client = _FakeLLMClient([LLMStreamChunk(delta="hello", finish_reason="stop")])
    service = QAService(rag_engine, llm_client)  # type: ignore[arg-type]

    events = _collect_events(service.stream_answer(_request(resource_ids=[])))

    assert [event.event_type for event in events] == ["chunk", "done"]
    assert rag_engine.requests == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (RetrievalUnavailableError("检索不可用"), "RETRIEVAL_UNAVAILABLE"),
        (LlamaIndexRetrievalForbiddenError("无权访问资源"), "RETRIEVAL_FORBIDDEN"),
    ],
)
def test_stream_answer_rag_errors_emit_sanitized_error_events(
    error: Exception,
    code: str,
) -> None:
    rag_engine = _FakeRagEngine(error=error)
    service = QAService(rag_engine, _FakeLLMClient([]))  # type: ignore[arg-type]

    events = _collect_events(service.stream_answer(_request()))

    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].data["error_code"] == code
    assert "Traceback" not in str(events[0].data)
    assert "/Users/" not in str(events[0].data)


def test_stream_answer_empty_retrieval_result_can_complete() -> None:
    rag_engine = _FakeRagEngine(
        RetrievalResult(chunks=[], prompt="empty prompt", context_token_count=0)
    )
    llm_client = _FakeLLMClient([LLMStreamChunk(delta="answer", finish_reason="stop")])
    service = QAService(rag_engine, llm_client)  # type: ignore[arg-type]

    events = _collect_events(service.stream_answer(_request()))

    assert [event.event_type for event in events] == ["chunk", "done"]
    assert events[-1].data["citation_count"] == 0
    assert rag_engine.requests


def test_stream_answer_llm_failure_keeps_existing_error_contract() -> None:
    rag_engine = _FakeRagEngine(RetrievalResult(chunks=[], prompt="prompt", context_token_count=0))

    class _FailingLLMClient:
        async def stream_complete(self, request: object) -> AsyncIterator[LLMStreamChunk]:
            raise RuntimeError("llm down")
            yield LLMStreamChunk(delta="unreachable")  # noqa: B018

    service = QAService(rag_engine, _FailingLLMClient())  # type: ignore[arg-type]

    events = _collect_events(service.stream_answer(_request()))

    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].data["error_code"] == "LLM_STREAM_ERROR"

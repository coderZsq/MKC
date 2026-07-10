from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest
from tenacity import wait_none

from app.core.exceptions import LLMAuthFailedError, LLMTimeoutError, LLMUnavailableError
from app.services.llm.config import LLMConfig
from app.services.llm.llm_client import (
    LLMClient,
    format_sse_stream,
    sync_format_sse_stream,
)
from app.services.llm.models import LLMRequest, LLMResponse, LLMStreamChunk, Usage

pytestmark = pytest.mark.anyio


async def _collect_stream(stream: AsyncIterator) -> list:
    return [chunk async for chunk in stream]


def _make_request() -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        max_tokens=2048,
    )


def _make_response(content: str = "ok") -> LLMResponse:
    return LLMResponse(
        content=content,
        model="test-model",
        finish_reason="stop",
        usage=Usage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
    )


class TestLLMClientComplete:
    def test_complete_returns_provider_response(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = _make_response("primary")
        client = LLMClient(provider=provider, config=LLMConfig(max_retries=1))

        response = client.complete(_make_request())

        assert response.content == "primary"
        assert provider.complete.call_count == 1

    def test_complete_retries_then_succeeds(self, monkeypatch) -> None:
        provider = MagicMock()
        provider.complete.side_effect = [
            LLMUnavailableError(),
            LLMUnavailableError(),
            _make_response("success"),
        ]
        client = LLMClient(provider=provider, config=LLMConfig(max_retries=3))

        monkeypatch.setattr(
            "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
        )

        response = client.complete(_make_request())

        assert response.content == "success"
        assert provider.complete.call_count == 3

    def test_complete_retries_exhausted_then_raises(self, monkeypatch) -> None:
        provider = MagicMock()
        provider.complete.side_effect = LLMUnavailableError("still down")
        client = LLMClient(provider=provider, config=LLMConfig(max_retries=3))

        monkeypatch.setattr(
            "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
        )

        with pytest.raises(LLMUnavailableError):
            client.complete(_make_request())

        assert provider.complete.call_count == 3

    def test_complete_timeout_retried(self, monkeypatch) -> None:
        provider = MagicMock()
        provider.complete.side_effect = [LLMTimeoutError(), _make_response("ok")]
        client = LLMClient(provider=provider, config=LLMConfig(max_retries=2))

        monkeypatch.setattr(
            "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
        )

        response = client.complete(_make_request())

        assert response.content == "ok"
        assert provider.complete.call_count == 2

    def test_complete_auth_error_not_retried(self) -> None:
        provider = MagicMock()
        provider.complete.side_effect = LLMAuthFailedError()
        client = LLMClient(provider=provider, config=LLMConfig(max_retries=3))

        with pytest.raises(LLMAuthFailedError):
            client.complete(_make_request())

        assert provider.complete.call_count == 1

    def test_complete_uses_fallback_when_primary_fails(self, monkeypatch) -> None:
        primary = MagicMock()
        primary.complete.side_effect = LLMUnavailableError()
        fallback = MagicMock()
        fallback.complete.return_value = _make_response("fallback")
        client = LLMClient(
            provider=primary,
            fallback_provider=fallback,
            config=LLMConfig(max_retries=1),
        )

        monkeypatch.setattr(
            "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
        )

        response = client.complete(_make_request())

        assert response.content == "fallback"
        assert primary.complete.call_count == 1
        assert fallback.complete.call_count == 1

    def test_complete_without_fallback_propagates_error(self, monkeypatch) -> None:
        provider = MagicMock()
        provider.complete.side_effect = LLMUnavailableError()
        client = LLMClient(provider=provider, config=LLMConfig(max_retries=1))

        monkeypatch.setattr(
            "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
        )

        with pytest.raises(LLMUnavailableError):
            client.complete(_make_request())


class TestLLMClientStream:
    async def test_stream_complete_yields_chunks(self) -> None:
        async def _provider_stream(request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
            yield LLMStreamChunk(delta="hi")
            yield LLMStreamChunk(delta="!")

        provider = MagicMock()
        provider.stream_complete.return_value = _provider_stream(_make_request())
        client = LLMClient(provider=provider)

        chunks = [chunk async for chunk in client.stream_complete(_make_request())]

        assert [chunk.delta for chunk in chunks] == ["hi", "!"]

    async def test_stream_complete_yields_error_chunk_on_failure(self) -> None:
        async def _failing_stream(request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
            yield LLMStreamChunk(delta="partial")
            raise LLMUnavailableError("interrupted")

        provider = MagicMock()
        provider.stream_complete.return_value = _failing_stream(_make_request())
        client = LLMClient(provider=provider)

        chunks = [chunk async for chunk in client.stream_complete(_make_request())]

        assert chunks[0].delta == "partial"
        assert chunks[-1].finish_reason == "error"

    async def test_stream_complete_timeout_yields_error_chunk(self) -> None:
        async def _failing_stream(request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
            yield LLMStreamChunk(delta="partial")
            raise LLMTimeoutError()

        provider = MagicMock()
        provider.stream_complete.return_value = _failing_stream(_make_request())
        client = LLMClient(provider=provider)

        chunks = [chunk async for chunk in client.stream_complete(_make_request())]

        assert chunks[-1].finish_reason == "error"


class TestSSEHelpers:
    async def test_format_sse_stream(self) -> None:
        async def _chunks() -> AsyncIterator[LLMStreamChunk]:
            yield LLMStreamChunk(delta="one")
            yield LLMStreamChunk(delta="two")

        events = [event async for event in format_sse_stream(_chunks())]

        assert events[0] == 'event: message\ndata: {"delta":"one"}\n\n'
        assert events[1] == 'event: message\ndata: {"delta":"two"}\n\n'
        assert events[2] == 'event: done\ndata: {"finish_reason":"stop"}\n\n'

    def test_sync_format_sse_stream(self) -> None:
        async def _chunks() -> AsyncIterator[LLMStreamChunk]:
            yield LLMStreamChunk(delta="a")

        events = list(sync_format_sse_stream(format_sse_stream(_chunks())))

        assert len(events) == 2
        assert 'event: message\ndata: {"delta":"a"}' in events[0]
        assert 'event: done\ndata: {"finish_reason":"stop"}' in events[1]

    def test_sync_format_sse_stream_can_run_in_existing_loop(self) -> None:
        async def _chunks() -> AsyncIterator[LLMStreamChunk]:
            yield LLMStreamChunk(delta="b")

        async def _runner() -> list[str]:
            return list(sync_format_sse_stream(format_sse_stream(_chunks())))

        events = asyncio.run(_runner())
        assert any('"delta":"b"' in event for event in events)

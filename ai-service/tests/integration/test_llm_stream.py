from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.exceptions import LLMUnavailableError
from app.services.llm.models import LLMStreamChunk

INTERNAL_KEY = os.environ["INTERNAL_API_KEY"]


@pytest.mark.integration
def test_llm_stream_success(client) -> None:
    response = client.post(
        "/ai/v1/llm/stream",
        json={"messages": [{"role": "user", "content": "hello"}]},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/event-stream"
    body = response.data.decode("utf-8")
    assert "event: message" in body
    assert "event: done" in body


@pytest.mark.integration
def test_llm_stream_rejects_missing_key(client) -> None:
    response = client.post(
        "/ai/v1/llm/stream",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False


@pytest.mark.integration
def test_llm_stream_validates_request(client) -> None:
    response = client.post(
        "/ai/v1/llm/stream",
        json={"temperature": 5.0},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.integration
def test_llm_stream_emits_error_on_provider_failure(client) -> None:
    async def _failing_stream(request) -> None:
        yield LLMStreamChunk(delta="partial")
        raise LLMUnavailableError("stream failed")

    with patch.object(
        client.application.extensions["llm"]._provider,
        "stream_complete",
        new=_failing_stream,
    ):
        response = client.post(
            "/ai/v1/llm/stream",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers={"X-Internal-Key": INTERNAL_KEY},
        )

    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "event: message" in body
    assert '"finish_reason":"error"' in body
    assert "event: done" in body


@pytest.mark.integration
def test_llm_stream_sse_events_are_separated(client) -> None:
    async def _chunks(request) -> None:
        yield LLMStreamChunk(delta="hello")
        yield LLMStreamChunk(delta=" world")

    with patch.object(
        client.application.extensions["llm"],
        "stream_complete",
        new=_chunks,
    ):
        response = client.post(
            "/ai/v1/llm/stream",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers={"X-Internal-Key": INTERNAL_KEY},
        )

    body = response.data.decode("utf-8")
    events = [line for line in body.split("\n") if line.startswith("event:")]
    assert events == ["event: message", "event: message", "event: done"]

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.llm.models import LLMStreamChunk
from app.services.retrieval.retrieval_service import RetrievalService

INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]


def _parse_sse_events(body: str) -> list[dict[str, Any]]:
    events = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type: str | None = None
        data: dict[str, Any] | None = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line.replace("event: ", "", 1).strip()
            elif line.startswith("data:"):
                data = json.loads(line.replace("data: ", "", 1))
        events.append({"event_type": event_type, "data": data})
    return events


def _post(
    client: FlaskClient,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    merged_headers = {"X-Internal-Key": INTERNAL_API_KEY}
    if headers:
        merged_headers.update(headers)
    return client.post(
        "/ai/v1/qa/stream",
        headers=merged_headers,
        json=payload,
    )


@pytest.mark.integration
def test_qa_stream_success(client: FlaskClient) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.return_value = RetrievalResult(
        chunks=[
            RetrievalChunk(
                chunk_id="c-1",
                resource_id="res-1",
                text="topic",
                score=0.91,
                metadata={"page": 2, "resource_type": "pdf"},
            ),
        ],
        prompt="contextual prompt",
        context_token_count=5,
    )
    client.application.extensions["retrieval"] = retrieval_service

    async def _stream_with_citation(_request: object) -> Any:
        yield LLMStreamChunk(delta="topic answer [^1]", finish_reason="stop")

    client.application.extensions["llm"].stream_complete = _stream_with_citation

    response = _post(
        client,
        {
            "question": "What is the topic?",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "user_id": "user-1",
            "resource_ids": ["res-1"],
        },
    )

    assert response.status_code == 200
    assert response.content_type == "text/event-stream"
    body = response.data.decode("utf-8")
    events = _parse_sse_events(body)
    event_types = [e.get("event_type") for e in events]
    assert "chunk" in event_types
    assert "done" in event_types
    citation = next(e for e in events if e.get("event_type") == "citation")
    assert citation["data"]["index"] == 1
    assert citation["data"]["chunk_id"] == "c-1"
    assert citation["data"]["resource_id"] == "res-1"
    assert citation["data"]["resource_type"] == "pdf"
    assert citation["data"]["page"] == 2
    assert citation["data"]["snippet"] == "topic"
    assert events[-1]["data"]["citation_count"] == 1
    assert all(
        e["data"]["message_id"] == "msg-1"
        for e in events
        if e["data"] and "message_id" in e["data"]
    )


@pytest.mark.integration
def test_qa_stream_validates_request(client: FlaskClient) -> None:
    response = _post(
        client,
        {"temperature": 5.0},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.integration
def test_qa_stream_rejects_missing_key(client: FlaskClient) -> None:
    response = client.post(
        "/ai/v1/qa/stream",
        json={
            "question": "What is the topic?",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "user_id": "user-1",
            "resource_ids": ["res-1"],
        },
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.integration
def test_qa_stream_emits_error_on_retrieval_failure(client: FlaskClient) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.side_effect = RuntimeError("store down")
    client.application.extensions["retrieval"] = retrieval_service

    response = _post(
        client,
        {
            "question": "What is the topic?",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "user_id": "user-1",
            "resource_ids": ["res-1"],
        },
    )

    assert response.status_code == 200
    body = response.data.decode("utf-8")
    events = _parse_sse_events(body)
    assert len(events) == 1
    assert events[0]["event_type"] == "error"
    assert events[0]["data"]["error_code"] == "RETRIEVAL_UNAVAILABLE"


@pytest.mark.integration
def test_qa_stream_emits_error_on_llm_failure(client: FlaskClient) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.return_value = RetrievalResult(
        chunks=[], prompt="prompt", context_token_count=0
    )
    client.application.extensions["retrieval"] = retrieval_service

    async def _failing_stream(_request: object) -> Any:
        raise RuntimeError("llm down")
        yield  # noqa: B001

    with patch.object(client.application.extensions["llm"], "stream_complete", new=_failing_stream):
        response = _post(
            client,
            {
                "question": "What is the topic?",
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "user_id": "user-1",
                "resource_ids": ["res-1"],
            },
        )

    assert response.status_code == 200
    body = response.data.decode("utf-8")
    events = _parse_sse_events(body)
    assert len(events) == 1
    assert events[0]["event_type"] == "error"
    assert events[0]["data"]["error_code"] == "LLM_STREAM_ERROR"

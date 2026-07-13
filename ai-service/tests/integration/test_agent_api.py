from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from flask.testing import FlaskClient

from app.core.exceptions import RetrievalForbiddenError
from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.llm.models import LLMStreamChunk

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


def _post(client: FlaskClient, payload: dict[str, Any], key: str | None = INTERNAL_API_KEY) -> Any:
    headers = {"X-Internal-Key": key} if key is not None else {}
    return client.post("/ai/v1/agent/run", headers=headers, json=payload)


@pytest.mark.integration
def test_agent_run_returns_sse_stream(client: FlaskClient) -> None:
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        chunks=[
            RetrievalChunk(
                chunk_id="c-1",
                resource_id="res-1",
                text="topic",
                score=0.91,
                metadata={"page": 2},
            )
        ],
        prompt="prompt",
        context_token_count=1,
    )
    client.application.extensions["retrieval"] = retrieval

    async def _stream(_request: object) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(delta="hello")
        yield LLMStreamChunk(delta="", finish_reason="stop")

    client.application.extensions["llm"].stream_complete = _stream

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
    events = _parse_sse_events(response.data.decode("utf-8"))
    event_types = [event["event_type"] for event in events]
    assert "node_start" in event_types
    assert "chunk" in event_types
    assert "citation" in event_types
    assert event_types[-1] == "done"


@pytest.mark.integration
def test_agent_run_rejects_missing_and_invalid_key(client: FlaskClient) -> None:
    payload = {
        "question": "q",
        "conversation_id": "conv-1",
        "message_id": "msg-1",
        "user_id": "user-1",
    }
    missing = _post(client, payload, key=None)
    assert missing.status_code == 401
    assert missing.get_json()["error"]["code"] == "UNAUTHORIZED"

    invalid = _post(client, payload, key="bad")
    assert invalid.status_code == 401
    assert invalid.get_json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.integration
def test_agent_run_validates_request(client: FlaskClient) -> None:
    response = _post(client, {"temperature": 5.0})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.integration
def test_agent_run_emits_forbidden_on_resource_scope_violation(client: FlaskClient) -> None:
    retrieval = MagicMock()
    retrieval.retrieve.side_effect = RetrievalForbiddenError()
    client.application.extensions["retrieval"] = retrieval

    response = _post(
        client,
        {
            "question": "q",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "user_id": "user-1",
            "resource_ids": ["other-resource"],
        },
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.data.decode("utf-8"))
    assert events[-1]["event_type"] == "error"
    assert events[-1]["data"]["error_code"] == "FORBIDDEN"

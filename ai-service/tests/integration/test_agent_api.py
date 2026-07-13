from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import chromadb
import pytest
from flask.testing import FlaskClient

from app.core.exceptions import RetrievalForbiddenError
from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.llm.models import LLMStreamChunk
from app.services.memory import MemoryConfig, build_memory_service
from app.vector_store import ChromaStore
from app.vector_store.config import build_vector_store_config

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
        yield LLMStreamChunk(delta="hello [^1]")
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
    citation = next(event for event in events if event["event_type"] == "citation")
    assert citation["data"]["index"] == 1
    assert citation["data"]["chunk_id"] == "c-1"
    assert citation["data"]["resource_id"] == "res-1"
    assert citation["data"]["resource_type"] == "pdf"
    assert citation["data"]["page"] == 2
    assert citation["data"]["snippet"] == "topic"
    assert event_types[-1] == "done"
    assert events[-1]["data"]["citation_count"] == 1


@pytest.mark.integration
def test_agent_run_recalls_long_term_memory(client: FlaskClient) -> None:
    """A second request with no history still sees a fact saved in a previous turn."""
    captured_requests: list[object] = []
    llm = client.application.extensions["llm"]

    async def _capture_stream(request: object) -> AsyncIterator[LLMStreamChunk]:
        captured_requests.append(request)
        yield LLMStreamChunk(delta="ok")
        yield LLMStreamChunk(delta="", finish_reason="stop")

    llm.stream_complete = MagicMock(side_effect=_capture_stream)

    # Use an isolated in-memory collection for long-term memory so this test
    # does not pollute the shared vector store collection used by other tests.
    embedding = client.application.extensions["embedding"]
    store_config = build_vector_store_config()
    store_config.provider = "chroma"
    store_config.collection_name = "mkc_memory_test"
    store_config.chroma_path = ":memory:"
    memory_store = ChromaStore(store_config, client=chromadb.Client())
    client.application.extensions["memory_service"] = build_memory_service(
        embedding,
        memory_store,
        config=MemoryConfig(
            enabled=True,
            top_k=5,
            score_threshold=0.0,
            max_context_tokens=2048,
        ),
    )

    response = _post(
        client,
        {
            "question": "我叫 Alice",
            "conversation_id": "conv-memory",
            "message_id": "msg-1",
            "user_id": "user-memory",
            "resource_ids": [],
        },
    )
    assert response.status_code == 200
    _ = response.get_data()

    response = _post(
        client,
        {
            "question": "我叫什么",
            "conversation_id": "conv-memory",
            "message_id": "msg-2",
            "user_id": "user-memory",
            "resource_ids": [],
        },
    )
    assert response.status_code == 200
    _ = response.get_data()

    # The second LLM request should include the long-term memory context.
    second_request = captured_requests[-1]
    assert second_request.messages[0].role == "system"
    assert "Alice" in second_request.messages[0].content


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

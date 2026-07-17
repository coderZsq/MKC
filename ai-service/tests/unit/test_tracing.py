from __future__ import annotations

import logging

import pytest
from flask import Flask, g
from flask.testing import FlaskClient

from app.core.logger import get_logger
from app.core.response import make_response
from app.observability.tracing import extract_trace_id, is_safe_attribute, start_span

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{TRACE_ID}-00f067aa0ba902b7-01"


def test_extract_trace_id_accepts_valid_traceparent() -> None:
    assert extract_trace_id(TRACEPARENT) == TRACE_ID


def test_extract_trace_id_rejects_invalid_traceparent() -> None:
    # MKC-TC-S5-3-009: invalid traceparent degrades to a new trace instead of crashing.
    assert extract_trace_id("not-a-traceparent") is None


def test_ai_service_continues_trace_context(client: FlaskClient) -> None:
    # MKC-TC-S5-3-002: AI Service response uses Gateway trace id from traceparent.
    response = client.get("/api/v1/health", headers={"traceparent": TRACEPARENT})

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == TRACE_ID
    assert response.get_json()["trace_id"] == TRACE_ID


def test_ai_service_invalid_traceparent_creates_trace(client: FlaskClient) -> None:
    response = client.get("/api/v1/health", headers={"traceparent": "bad"})

    assert response.status_code == 200
    assert len(response.headers["X-Trace-Id"]) == 32
    assert response.headers["X-Trace-Id"] != "bad"


def test_business_span_records_safe_attributes() -> None:
    # MKC-TC-S5-3-003, MKC-TC-S5-3-005: business spans are created and sanitized.
    app = Flask(__name__)
    with app.test_request_context("/ai/v1/test", headers={"traceparent": TRACEPARENT}):
        g.trace_id = TRACE_ID
        g.span_records = []
        with start_span(
            "rag.retrieve",
            {
                "resource.count": 2,
                "retrieval.top_k": 5,
                "question": "raw user question should not be recorded",
                "authorization": "Bearer secret",
            },
        ):
            pass

        assert len(g.span_records) == 1
        span = g.span_records[0]
        assert span.name == "rag.retrieve"
        assert span.attributes["resource.count"] == 2
        assert span.attributes["retrieval.top_k"] == 5
        assert "question" not in span.attributes
        assert "authorization" not in span.attributes


def test_business_span_marks_error() -> None:
    # MKC-TC-S5-3-007: business exceptions mark span status as ERROR with sanitized code.
    app = Flask(__name__)
    with app.test_request_context("/ai/v1/test"):
        g.trace_id = TRACE_ID
        g.span_records = []
        try:
            with start_span("llm.stream"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        assert g.span_records[0].status == "ERROR"
        assert g.span_records[0].attributes["error.code"] == "RUNTIMEERROR"


def test_logger_includes_trace_id(caplog: pytest.LogCaptureFixture) -> None:
    # MKC-TC-S5-3-006: structured logs include trace_id.
    app = Flask(__name__)
    logger = get_logger("test.trace.logger")
    logger.propagate = True
    with app.test_request_context("/test"):
        g.request_id = "req-1"
        g.trace_id = TRACE_ID
        with caplog.at_level(logging.INFO):
            logger.info("hello trace")

    assert any(getattr(record, "trace_id", "") == TRACE_ID for record in caplog.records)


def test_response_includes_trace_id() -> None:
    app = Flask(__name__)
    with app.test_request_context("/test"):
        g.trace_id = TRACE_ID
        response, status = make_response(data={"ok": True})

    assert status == 200
    assert response.get_json()["trace_id"] == TRACE_ID


def test_attribute_allowlist_rejects_sensitive_content() -> None:
    assert is_safe_attribute("resource.count", 1)
    assert not is_safe_attribute("llm.prompt", "contains token value")
    assert not is_safe_attribute("jwt", "abc")

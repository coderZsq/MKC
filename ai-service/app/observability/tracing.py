from __future__ import annotations

import contextlib
import re
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from flask import Flask, Response, g, has_request_context, request

TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
SENSITIVE_MARKERS = ("authorization", "jwt", "token", "api_key", "secret", "password", "question")
ALLOWED_ATTRIBUTE_PREFIXES = (
    "http.",
    "resource.",
    "task.",
    "retrieval.",
    "llm.",
    "embedding.",
    "sse.",
    "error.",
)


@dataclass
class SpanRecord:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"
    error_code: str | None = None
    started_at: float = field(default_factory=time.monotonic)
    ended_at: float | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        if is_safe_attribute(key, value):
            self.attributes[key] = value

    def mark_error(self, error_code: str) -> None:
        self.status = "ERROR"
        self.error_code = sanitize_error_code(error_code)
        self.attributes["error.code"] = self.error_code

    def end(self) -> None:
        self.ended_at = time.monotonic()


def init_tracing(app: Flask) -> None:
    app.extensions["tracing_enabled"] = bool(app.config.get("TRACING_ENABLED", True))

    @app.before_request
    def start_request_trace() -> None:
        trace_id = extract_trace_id(request.headers.get("traceparent")) or secrets.token_hex(16)
        g.trace_id = trace_id
        g.span_records = []
        g.root_span = SpanRecord(
            name=f"{request.method} {request.path}",
            attributes={
                "http.request.method": request.method,
                "url.path": request.path,
            },
        )

    @app.after_request
    def finish_request_trace(response: Response) -> Response:
        root_span = getattr(g, "root_span", None)
        if isinstance(root_span, SpanRecord):
            root_span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                root_span.mark_error(str(response.status_code))
            root_span.end()
            getattr(g, "span_records", []).insert(0, root_span)
        response.headers["X-Trace-Id"] = get_trace_id()
        return response


def get_trace_id() -> str:
    if not has_request_context():
        return ""
    return getattr(g, "trace_id", "")


@contextlib.contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[SpanRecord]:
    span_record = SpanRecord(name=name)
    for key, value in (attributes or {}).items():
        span_record.set_attribute(key, value)
    try:
        yield span_record
    except Exception as exc:
        span_record.mark_error(getattr(exc, "code", exc.__class__.__name__))
        raise
    finally:
        span_record.end()
        if has_request_context():
            getattr(g, "span_records", []).append(span_record)


def extract_trace_id(traceparent: str | None) -> str | None:
    if not traceparent:
        return None
    match = TRACEPARENT_RE.match(traceparent.strip())
    if not match:
        return None
    return match.group(1)


def is_safe_attribute(key: str, value: Any) -> bool:
    lowered_key = key.lower()
    if any(marker in lowered_key for marker in SENSITIVE_MARKERS):
        return False
    if not lowered_key.startswith(ALLOWED_ATTRIBUTE_PREFIXES) and lowered_key not in {
        "url.path",
        "model.provider",
    }:
        return False
    return not (
        isinstance(value, str) and any(marker in value.lower() for marker in SENSITIVE_MARKERS)
    )


def sanitize_error_code(error_code: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "_", error_code.upper())[:80]

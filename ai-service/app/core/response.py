import json
from datetime import UTC, datetime
from typing import Any

from flask import Response, g, has_request_context

RETRYABLE_CODES = {
    "DEPENDENCY_UNAVAILABLE",
    "EMBEDDING_UNAVAILABLE",
    "LLM_STREAM_ERROR",
    "LLM_TIMEOUT",
    "LLM_UNAVAILABLE",
    "RETRIEVAL_TIMEOUT",
    "RETRIEVAL_UNAVAILABLE",
    "VECTOR_STORE_UNAVAILABLE",
}


def make_response(
    data: Any = None,
    success: bool = True,
    error: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    status: int = 200,
) -> tuple[Response, int]:
    trace_id = getattr(g, "trace_id", "") if has_request_context() else ""
    error_payload = normalize_error(error, status=status, trace_id=trace_id)
    payload = {
        "success": success,
        "data": data,
        "error": error_payload,
        "meta": meta or {"timestamp": datetime.now(UTC).isoformat()},
    }
    if trace_id:
        payload["trace_id"] = trace_id
    response = Response(
        json.dumps(payload, ensure_ascii=False, default=str),
        status=status,
        mimetype="application/json",
    )
    return response, status


def normalize_error(
    error: dict[str, Any] | None,
    *,
    status: int,
    trace_id: str = "",
) -> dict[str, Any] | None:
    if error is None:
        return None
    code = str(error.get("code") or "INTERNAL_ERROR")
    return {
        "code": code,
        "message": sanitize_message(str(error.get("message") or "系统异常，请稍后重试")),
        "trace_id": trace_id,
        "retryable": is_retryable(status, code),
        "details": _safe_details(error.get("details")),
    }


def is_retryable(status: int, code: str) -> bool:
    return status in {408, 429, 503, 504} or code in RETRYABLE_CODES


def sanitize_message(message: str) -> str:
    lowered = message.lower()
    sensitive = (
        "traceback",
        "sql",
        "select ",
        "insert ",
        "update ",
        "delete ",
        "password",
        "secret",
        "token",
        "/users/",
    )
    if any(marker in lowered for marker in sensitive):
        return "系统异常，请稍后重试"
    return message[:200]


def _safe_details(details: Any) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}
    safe: dict[str, Any] = {}
    for key, value in details.items():
        key_text = str(key)
        if any(marker in key_text.lower() for marker in ("password", "secret", "token", "key")):
            continue
        safe[key_text[:80]] = str(value)[:200]
    return safe

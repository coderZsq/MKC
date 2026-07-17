import json
from datetime import UTC, datetime
from typing import Any

from flask import Response, g, has_request_context


def make_response(
    data: Any = None,
    success: bool = True,
    error: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    status: int = 200,
) -> tuple[Response, int]:
    payload = {
        "success": success,
        "data": data,
        "error": error,
        "meta": meta or {"timestamp": datetime.now(UTC).isoformat()},
    }
    trace_id = getattr(g, "trace_id", "") if has_request_context() else ""
    if trace_id:
        payload["trace_id"] = trace_id
    response = Response(
        json.dumps(payload, ensure_ascii=False, default=str),
        status=status,
        mimetype="application/json",
    )
    return response, status

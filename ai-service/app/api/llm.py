from __future__ import annotations

import logging

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import APIException, LLMUnavailableError, ValidationException
from app.core.response import make_response
from app.services.llm.llm_client import format_sse_stream, sync_format_sse_stream
from app.services.llm.models import LLMRequest

logger = logging.getLogger(__name__)

llm_bp = Blueprint("llm", __name__)
llm_bp.before_request(check_internal_key)


@llm_bp.post("/llm/complete")
def complete() -> tuple[Response, int]:
    """Synchronously generate a complete LLM response."""
    data = request.get_json(silent=True) or {}
    try:
        req = LLMRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("LLM request validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    client = current_app.extensions["llm"]
    try:
        response = client.complete(req)
    except APIException:
        raise
    except Exception as exc:
        logger.exception("LLM complete failed")
        raise LLMUnavailableError() from exc

    return make_response(data=response.model_dump(), status=200)


@llm_bp.post("/llm/stream")
def stream() -> Response:
    """Stream an LLM response as Server-Sent Events."""
    data = request.get_json(silent=True) or {}
    try:
        req = LLMRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("LLM stream request validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    client = current_app.extensions["llm"]
    sse_stream = sync_format_sse_stream(format_sse_stream(client.stream_complete(req)))

    return Response(
        sse_stream,
        status=200,
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

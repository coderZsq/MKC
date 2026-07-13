from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import APIException, LLMUnavailableError, ValidationException
from app.models.qa import QARequest
from app.services.llm.llm_client import sync_format_sse_stream
from app.services.qa_service import QAService

logger = logging.getLogger(__name__)

qa_bp = Blueprint("qa", __name__)
qa_bp.before_request(check_internal_key)


@qa_bp.post("/qa/stream")
def stream_qa() -> Response:
    """Stream a question-answer response as Server-Sent Events."""
    data = request.get_json(silent=True) or {}
    try:
        req = QARequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("QA request validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    retrieval_service = current_app.extensions["retrieval"]
    llm_client = current_app.extensions["llm"]
    citation_service = current_app.extensions.get("citation_service")
    memory_service = current_app.extensions.get("memory_service")
    service = QAService(
        retrieval_service, llm_client, citation_service=citation_service, memory_service=memory_service
    )

    async def _generate() -> AsyncIterator[str]:
        async for event in service.stream_answer(req):
            yield event.format_sse()

    try:
        return Response(
            sync_format_sse_stream(_generate()),
            status=200,
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except APIException:
        raise
    except Exception as exc:
        logger.exception("QA stream failed")
        raise LLMUnavailableError() from exc

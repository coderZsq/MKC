from __future__ import annotations

import logging

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import APIException, RetrievalUnavailableError, ValidationException
from app.core.response import make_response
from app.models.retrieval import RetrievalRequest

logger = logging.getLogger(__name__)

retrieval_bp = Blueprint("retrieval", __name__)
retrieval_bp.before_request(check_internal_key)


@retrieval_bp.post("/retrieve")
def retrieve_context() -> tuple[Response, int]:
    """Retrieve relevant chunks and assemble a prompt for the given question."""
    data = request.get_json(silent=True) or {}
    try:
        req = RetrievalRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Retrieval request validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    service = current_app.extensions["retrieval"]

    try:
        result = service.retrieve(req)
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Retrieval failed")
        raise RetrievalUnavailableError() from exc

    return make_response(
        data={
            "chunks": [chunk.model_dump() for chunk in result.chunks],
            "prompt": result.prompt,
            "context_token_count": result.context_token_count,
        },
        status=200,
    )

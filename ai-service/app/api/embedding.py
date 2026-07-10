from __future__ import annotations

import logging

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import (
    APIException,
    EmbeddingInternalError,
    EmptyBatchError,
    ValidationException,
)
from app.core.response import make_response
from app.models.embedding import EmbeddingRequest

logger = logging.getLogger(__name__)

embedding_bp = Blueprint("embedding", __name__)
embedding_bp.before_request(check_internal_key)


@embedding_bp.post("/embed")
def embed_chunks() -> tuple[Response, int]:
    """Generate dense embeddings for a batch of text chunks."""
    data = request.get_json(silent=True) or {}
    try:
        req = EmbeddingRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Embedding request validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    if not req.chunks:
        raise EmptyBatchError()

    service = current_app.extensions["embedding"]
    try:
        embeddings = service.embed(req.chunks)
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Embedding generation failed")
        raise EmbeddingInternalError() from exc

    return make_response(
        data={"embeddings": [embedding.model_dump() for embedding in embeddings]},
        status=200,
    )

from __future__ import annotations

import logging

from flask import Blueprint, Response, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import APIException, ChunkingError, ValidationException
from app.core.response import make_response
from app.models.chunk import ChunkRequest
from app.services.chunking.factory import build_chunking_config, build_chunking_service

logger = logging.getLogger(__name__)

chunking_bp = Blueprint("chunking", __name__)
chunking_bp.before_request(check_internal_key)


@chunking_bp.post("/chunk")
def chunk_text() -> tuple[Response, int]:
    """Split text into chunks using the configured or requested strategy."""
    data = request.get_json(silent=True) or {}
    try:
        req = ChunkRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationException(f"请求参数错误: {exc}") from exc

    config = build_chunking_config()
    if len(req.text) > config.max_input_chars:
        raise APIException(
            "TEXT_TOO_LONG",
            f"输入文本超过最大长度限制 {config.max_input_chars} 字符",
            400,
        )

    service = build_chunking_service(config=config)

    try:
        chunks = service.chunk(
            text=req.text,
            resource_id=req.resource_id,
            metadata=req.metadata,
            strategy=req.strategy,
        )
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Chunking failed for resource_id=%s", req.resource_id)
        raise ChunkingError() from exc

    return make_response(
        data={"chunks": [chunk.model_dump() for chunk in chunks]},
        status=200,
    )

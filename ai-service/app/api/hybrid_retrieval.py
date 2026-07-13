from __future__ import annotations

import logging

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import (
    APIException,
    InvalidRequestError,
    RetrievalUnavailableError,
)
from app.core.response import make_response
from app.models.hybrid_retrieval import HybridRetrievalRequest

logger = logging.getLogger(__name__)

hybrid_retrieval_bp = Blueprint("hybrid_retrieval", __name__)
hybrid_retrieval_bp.before_request(check_internal_key)


@hybrid_retrieval_bp.post("/retrieve/hybrid")
def retrieve_hybrid() -> tuple[Response, int]:
    """Run hybrid (BM25 + vector + RRF + cross-encoder) retrieval for a question."""
    data = request.get_json(silent=True) or {}
    try:
        req = HybridRetrievalRequest.model_validate(data)
    except PydanticValidationError as exc:
        field = ", ".join(str(err.get("loc", ())) for err in exc.errors())
        logger.warning("Hybrid retrieval request validation failed for fields: %s", field)
        raise InvalidRequestError("缺少问题或资源范围") from exc

    service = current_app.extensions["hybrid_retrieval"]

    try:
        result = service.retrieve(req)
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Hybrid retrieval failed")
        raise RetrievalUnavailableError() from exc

    return make_response(
        data={
            "chunks": [chunk.model_dump(exclude={"user_id"}) for chunk in result.chunks],
            "fusion": result.fusion.model_dump(),
            "degraded": result.degraded,
            "elapsed_ms": result.elapsed_ms,
        },
        status=200,
    )

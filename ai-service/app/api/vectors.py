from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import check_internal_key
from app.core.exceptions import (
    APIException,
    EmptyBatchError,
    ValidationException,
    VectorStoreError,
)
from app.core.response import make_response
from app.models.vector_record import (
    VectorDeleteRequest,
    VectorSearchRequest,
    VectorSearchResult,
    VectorUpsertRequest,
)

logger = logging.getLogger(__name__)

vectors_bp = Blueprint("vectors", __name__)
vectors_bp.before_request(check_internal_key)


def _get_store() -> Any:
    return current_app.extensions["vector_store"]


@vectors_bp.post("/vectors/upsert")
def upsert_vectors() -> tuple[Response, int]:
    """Upsert a batch of vector records into the configured vector store."""
    data = request.get_json(silent=True) or {}
    try:
        req = VectorUpsertRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Vector upsert validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    if not req.records:
        raise EmptyBatchError()

    store = _get_store()
    try:
        upserted_count = store.upsert(req.records)
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Vector upsert failed")
        raise VectorStoreError("向量写入失败") from exc

    return make_response(data={"upserted_count": upserted_count}, status=200)


@vectors_bp.post("/vectors/delete")
def delete_vectors() -> tuple[Response, int]:
    """Delete all vectors that belong to a resource (optionally scoped by user)."""
    data = request.get_json(silent=True) or {}
    try:
        req = VectorDeleteRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Vector delete validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    store = _get_store()
    try:
        deleted_count = store.delete_by_resource(req.resource_id, req.user_id)
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Vector delete failed")
        raise VectorStoreError("向量删除失败") from exc

    return make_response(data={"deleted_count": deleted_count}, status=200)


@vectors_bp.post("/vectors/search")
def search_vectors() -> tuple[Response, int]:
    """Search stored vectors by similarity to a query vector."""
    data = request.get_json(silent=True) or {}
    try:
        req = VectorSearchRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Vector search validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    store = _get_store()
    try:
        results: list[VectorSearchResult] = store.search(
            vector=req.vector,
            top_k=req.top_k,
            filters=req.filters,
        )
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Vector search failed")
        raise VectorStoreError("向量搜索失败") from exc

    return make_response(
        data={"results": [result.model_dump() for result in results]},
        status=200,
    )

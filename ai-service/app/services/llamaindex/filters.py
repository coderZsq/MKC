from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidRetrievalFilterError


def build_metadata_filters(user_id: str, resource_ids: list[str]) -> dict[str, Any]:
    """Build legacy vector-store filters for scoped retrieval."""
    normalized_user_id = user_id.strip()
    normalized_resource_ids = _normalize_resource_ids(resource_ids)
    if not normalized_user_id:
        raise InvalidRetrievalFilterError("检索过滤条件必须包含 user_id")
    if not normalized_resource_ids:
        raise InvalidRetrievalFilterError("检索过滤条件必须包含 resource_ids")
    return {
        "user_id": normalized_user_id,
        "resource_ids": normalized_resource_ids,
    }


def _normalize_resource_ids(resource_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for resource_id in resource_ids:
        value = resource_id.strip()
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized

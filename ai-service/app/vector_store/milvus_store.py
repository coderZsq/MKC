from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar, cast

from pymilvus import DataType, MilvusClient, MilvusException
from tenacity import (
    Retrying,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import VectorStoreConfigError, VectorStoreUnavailableError
from app.models.vector_record import VectorRecord, VectorSearchResult
from app.vector_store.config import VectorStoreConfig

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_ID_MAX_LENGTH: int = 64
_RESOURCE_ID_MAX_LENGTH: int = 64
_USER_ID_MAX_LENGTH: int = 64
_TEXT_MAX_LENGTH: int = 4096


class MilvusStore:
    """Milvus-backed vector store with tenacity retry and local-fallback index types."""

    def __init__(
        self,
        config: VectorStoreConfig,
        client: MilvusClient | None = None,
    ) -> None:
        self._config = config
        self._collection_name = config.collection_name
        self._client = client or self._create_client_with_retry()
        self._ensure_collection()

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        data = [_record_to_milvus(record) for record in records]

        def _upsert() -> dict[str, Any]:
            return cast(
                dict[str, Any],
                self._client.upsert(
                    collection_name=self._collection_name,
                    data=data,
                ),
            )

        result = self._with_retry(_upsert)
        return int(result.get("upsert_count", len(records)))

    def delete_by_resource(
        self,
        resource_id: str,
        user_id: str | None = None,
    ) -> int:
        expr = _resource_filter(resource_id, user_id)

        def _delete() -> dict[str, Any]:
            return cast(
                dict[str, Any],
                self._client.delete(
                    collection_name=self._collection_name,
                    filter=expr,
                ),
            )

        result = self._with_retry(_delete)
        if isinstance(result, list):
            return len(result)
        return int(result.get("delete_count", 0))

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        expr = _search_filter(filters or {})
        limit = min(top_k, self._config.top_k_limit)

        def _search() -> list[list[dict[str, Any]]]:
            return cast(
                list[list[dict[str, Any]]],
                self._client.search(
                    collection_name=self._collection_name,
                    data=[vector],
                    limit=limit,
                    filter=expr or None,
                    output_fields=[
                        "resource_id",
                        "user_id",
                        "text",
                        "metadata",
                        "created_at",
                    ],
                ),
            )

        search_results = self._with_retry(_search)
        if not search_results:
            return []
        return [
            _hit_to_result(hit, metric_type=self._config.metric_type) for hit in search_results[0]
        ]

    def _create_client_with_retry(self) -> MilvusClient:
        def _connect() -> MilvusClient:
            client = MilvusClient(
                uri=self._config.uri,
                db_name=self._config.db_name,
                token=self._config.token or None,
                user=self._config.user or None,
                password=self._config.password or None,
                timeout=self._config.connect_timeout,
            )
            client.list_collections()
            return client

        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._config.max_retries),
                wait=wait_exponential(
                    multiplier=1,
                    min=self._config.retry_min_wait,
                    max=self._config.retry_max_wait,
                ),
                reraise=True,
            ):
                with attempt:
                    return _connect()
        except Exception as exc:
            logger.exception("Failed to connect to Milvus after retries")
            raise VectorStoreUnavailableError("无法连接到 Milvus 向量存储") from exc

    def _ensure_collection(self) -> None:
        if self._client.has_collection(self._collection_name):
            self._validate_collection_dimension()
            return

        schema = self._build_schema()
        index_params = self._build_index_params()

        try:
            self._client.create_collection(
                collection_name=self._collection_name,
                schema=schema,
                index_params=index_params,
            )
            logger.info(
                "Created Milvus collection %s with %s index",
                self._collection_name,
                self._config.metric_type,
            )
        except MilvusException as exc:
            if "HNSW" in str(exc) or "local mode" in str(exc).lower():
                logger.warning("HNSW index unsupported in local Milvus, falling back to AUTOINDEX")
                index_params = self._build_index_params(index_type="AUTOINDEX")
                self._client.create_collection(
                    collection_name=self._collection_name,
                    schema=schema,
                    index_params=index_params,
                )
            else:
                raise

    def _build_schema(self) -> Any:
        schema = self._client.create_schema(auto_id=False)
        schema.add_field(
            field_name="id",
            datatype=DataType.VARCHAR,
            max_length=_ID_MAX_LENGTH,
            is_primary=True,
        )
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=self._config.dimensions,
        )
        schema.add_field(
            field_name="resource_id",
            datatype=DataType.VARCHAR,
            max_length=_RESOURCE_ID_MAX_LENGTH,
        )
        schema.add_field(
            field_name="user_id",
            datatype=DataType.VARCHAR,
            max_length=_USER_ID_MAX_LENGTH,
        )
        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=_TEXT_MAX_LENGTH,
        )
        schema.add_field(field_name="metadata", datatype=DataType.JSON)
        schema.add_field(field_name="created_at", datatype=DataType.INT64)
        return schema

    def _build_index_params(self, index_type: str | None = None) -> Any:
        params = self._client.prepare_index_params()
        params.add_index(
            field_name="vector",
            index_type=index_type or "HNSW",
            metric_type=self._config.metric_type,
            params={"M": 16, "efConstruction": 200},
        )
        return params

    def _validate_collection_dimension(self) -> None:
        description = self._client.describe_collection(self._collection_name)
        fields = description.get("fields", [])
        vector_field = next(
            (field for field in fields if field.get("name") == "vector"),
            None,
        )
        if vector_field is None:
            raise VectorStoreConfigError(f"Collection {self._collection_name} 缺少 vector 字段")
        actual_dim = vector_field.get("params", {}).get("dim")
        if actual_dim != self._config.dimensions:
            raise VectorStoreConfigError(
                f"Collection {self._collection_name} 维度 {actual_dim} "
                f"与配置 {self._config.dimensions} 不符"
            )

    def _with_retry(self, fn: Callable[[], _T]) -> _T:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._config.max_retries),
                wait=wait_exponential(
                    multiplier=1,
                    min=self._config.retry_min_wait,
                    max=self._config.retry_max_wait,
                ),
                reraise=True,
            ):
                with attempt:
                    return fn()
        except VectorStoreConfigError:
            raise
        except Exception as exc:
            logger.exception("Milvus operation failed after retries")
            raise VectorStoreUnavailableError("Milvus 操作失败，请重试") from exc
        raise AssertionError("unreachable")  # pragma: no cover


def _record_to_milvus(record: VectorRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "vector": record.vector,
        "resource_id": record.resource_id,
        "user_id": record.user_id,
        "text": record.text[:_TEXT_MAX_LENGTH],
        "metadata": record.metadata,
        "created_at": record.created_at,
    }


def _resource_filter(resource_id: str, user_id: str | None) -> str:
    resource_id = _escape_expr(resource_id)
    if user_id:
        return f"resource_id == '{resource_id}' && user_id == '{_escape_expr(user_id)}'"
    return f"resource_id == '{resource_id}'"


def _search_filter(filters: dict[str, Any]) -> str:
    clauses = []
    resource_ids = filters.get("resource_ids")
    if resource_ids is None:
        resource_ids = filters.get("resource_id")
    resource_filter = _resource_id_filter(resource_ids)
    if resource_filter:
        clauses.append(resource_filter)
    if "user_id" in filters:
        clauses.append(f"user_id == '{_escape_expr(str(filters['user_id']))}'")
    if not clauses:
        return ""
    return " && ".join(clauses)


def _resource_id_filter(resource_ids: Any) -> str:
    if resource_ids is None:
        return ""
    if isinstance(resource_ids, str):
        return f"resource_id == '{_escape_expr(resource_ids)}'"
    ids = [str(rid) for rid in resource_ids]
    if not ids:
        return "resource_id == ''"
    if len(ids) == 1:
        return f"resource_id == '{_escape_expr(ids[0])}'"
    escaped = [_escape_expr(rid) for rid in ids]
    items = ", ".join(f"'{rid}'" for rid in escaped)
    return f"resource_id in [{items}]"


def _escape_expr(value: str) -> str:
    return value.replace("'", "''")


def _hit_to_result(hit: dict[str, Any], metric_type: str) -> VectorSearchResult:
    entity = hit.get("entity", {})
    distance = float(hit["distance"])
    return VectorSearchResult(
        id=str(hit["id"]),
        resource_id=str(entity.get("resource_id", "")),
        user_id=str(entity.get("user_id", "")),
        text=str(entity.get("text", "")),
        metadata=entity.get("metadata", {}) or {},
        score=_distance_to_score(distance, metric_type),
        created_at=int(entity.get("created_at", 0)),
    )


def _distance_to_score(distance: float, metric_type: str) -> float:
    """Normalize a Milvus search distance to a [0, 1] similarity score.

    Milvus returns distances where smaller is better for every metric type.
    - COSINE: distance = 1 - cosine_similarity; map to ``1 - distance``.
    - L2: map with ``1 / (1 + distance)``.
    - IP: distance = -inner_product; map to ``-distance`` and clamp at 0.
    """
    metric = metric_type.upper()
    if metric == "L2":
        return 1.0 / (1.0 + distance)
    if metric == "IP":
        return max(0.0, -distance)
    # COSINE and anything else default to ``1 - distance``.
    return 1.0 - distance

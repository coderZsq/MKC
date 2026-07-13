from __future__ import annotations

import logging
from typing import Any

import chromadb

from app.core.exceptions import VectorStoreConfigError, VectorStoreUnavailableError
from app.models.vector_record import VectorRecord, VectorSearchResult
from app.vector_store.config import VectorStoreConfig

logger = logging.getLogger(__name__)


class ChromaStore:
    """ChromaDB-backed vector store used as a lightweight fallback."""

    def __init__(
        self,
        config: VectorStoreConfig,
        client: Any | None = None,
    ) -> None:
        self._config = config
        self._collection_name = config.collection_name
        self._client = client or chromadb.Client()
        self._collection = self._get_collection()

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        try:
            self._collection.upsert(
                ids=[record.id for record in records],
                embeddings=[record.vector for record in records],
                metadatas=[_record_to_chroma_metadata(record) for record in records],
                documents=[record.text for record in records],
            )
        except Exception as exc:
            logger.exception("Chroma upsert failed")
            raise VectorStoreUnavailableError("Chroma 写入失败") from exc
        return len(records)

    def delete_by_resource(
        self,
        resource_id: str,
        user_id: str | None = None,
    ) -> int:
        where_clause = _resource_filter(resource_id, user_id)
        before = int(self._collection.count())
        try:
            self._collection.delete(where=where_clause)
        except Exception as exc:
            logger.exception("Chroma delete failed")
            raise VectorStoreUnavailableError("Chroma 删除失败") from exc
        after = int(self._collection.count())
        return max(0, before - after)

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        where_clause = _search_filter(filters or {})
        n_results = min(top_k, self._config.top_k_limit)
        try:
            query_results = self._collection.query(
                query_embeddings=[vector],
                n_results=n_results,
                where=where_clause or None,
                include=["metadatas", "documents", "distances"],
            )
        except Exception as exc:
            logger.exception("Chroma search failed")
            raise VectorStoreUnavailableError("Chroma 搜索失败") from exc

        results: list[VectorSearchResult] = []
        ids = query_results.get("ids") or [[]]
        metadatas = query_results.get("metadatas") or [[]]
        documents = query_results.get("documents") or [[]]
        distances = query_results.get("distances") or [[]]
        for id_, metadata, document, distance in zip(
            ids[0], metadatas[0], documents[0], distances[0], strict=False
        ):
            if metadata is None:
                continue
            results.append(
                VectorSearchResult(
                    id=str(id_),
                    resource_id=str(metadata.get("resource_id", "")),
                    user_id=str(metadata.get("user_id", "")),
                    text=str(document) if document is not None else "",
                    metadata={k: v for k, v in metadata.items() if k not in _RESERVED_KEYS},
                    score=_distance_to_score(distance),
                    created_at=int(metadata.get("created_at", 0)),
                )
            )
        return results

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> list[VectorSearchResult]:
        """Fetch records matching ``filters`` without vector similarity.

        Used by hybrid retrieval to load the BM25 corpus. Returned scores are
        ``0.0`` because no similarity ranking is performed.
        """
        where_clause = _search_filter(filters or {})
        n_results = min(limit, self._config.top_k_limit)
        try:
            get_results = self._collection.get(
                where=where_clause or None,
                limit=n_results,
                include=["metadatas", "documents"],
            )
        except Exception as exc:
            logger.exception("Chroma query failed")
            raise VectorStoreUnavailableError("Chroma 查询失败") from exc

        results: list[VectorSearchResult] = []
        ids = get_results.get("ids") or []
        metadatas = get_results.get("metadatas") or []
        documents = get_results.get("documents") or []
        for id_, metadata, document in zip(ids, metadatas, documents, strict=False):
            if metadata is None:
                continue
            results.append(
                VectorSearchResult(
                    id=str(id_),
                    resource_id=str(metadata.get("resource_id", "")),
                    user_id=str(metadata.get("user_id", "")),
                    text=str(document) if document is not None else "",
                    metadata={k: v for k, v in metadata.items() if k not in _RESERVED_KEYS},
                    score=0.0,
                    created_at=int(metadata.get("created_at", 0)),
                )
            )
        return results

    def _get_collection(self) -> Any:
        try:
            return self._client.get_or_create_collection(
                self._collection_name,
                metadata={"hnsw:space": self._config.metric_type.lower()},
            )
        except Exception as exc:
            logger.exception("Failed to get or create Chroma collection")
            raise VectorStoreConfigError("无法初始化 Chroma collection") from exc


_RESERVED_KEYS = {"resource_id", "user_id", "created_at"}


def _record_to_chroma_metadata(record: VectorRecord) -> dict[str, Any]:
    return {
        "resource_id": record.resource_id,
        "user_id": record.user_id,
        "created_at": record.created_at,
        **record.metadata,
    }


def _resource_filter(resource_id: str, user_id: str | None) -> dict[str, Any]:
    if user_id is not None:
        return {
            "$and": [
                {"resource_id": resource_id},
                {"user_id": user_id},
            ]
        }
    return {"resource_id": resource_id}


def _search_filter(filters: dict[str, Any]) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    resource_ids = filters.get("resource_ids")
    if resource_ids is None:
        resource_ids = filters.get("resource_id")
    resource_filter = _resource_id_filter(resource_ids)
    if resource_filter is not None:
        clauses.append(resource_filter)
    if "user_id" in filters:
        clauses.append({"user_id": filters["user_id"]})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _resource_id_filter(resource_ids: Any) -> dict[str, Any] | None:
    if resource_ids is None:
        return None
    if isinstance(resource_ids, str):
        return {"resource_id": resource_ids}
    ids = [str(rid) for rid in resource_ids]
    if not ids:
        return {"resource_id": ""}
    if len(ids) == 1:
        return {"resource_id": ids[0]}
    return {"$or": [{"resource_id": rid} for rid in ids]}


def _distance_to_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return max(0.0, 1.0 - float(distance))

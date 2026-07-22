from __future__ import annotations

from typing import Any

from llama_index.core.schema import BaseNode, NodeWithScore, TextNode

from app.models.retrieval import RetrievalChunk
from app.models.vector_record import VectorRecord, VectorSearchResult


def vector_record_to_node(record: VectorRecord) -> TextNode:
    """Map a stored vector record to a LlamaIndex TextNode."""
    metadata = _metadata_with_required_fields(
        metadata=record.metadata,
        chunk_id=record.id,
        resource_id=record.resource_id,
        user_id=record.user_id,
    )
    return TextNode(id_=record.id, text=record.text or "", extra_info=metadata)


def vector_search_result_to_node(result: VectorSearchResult) -> TextNode:
    """Map a vector search result to a LlamaIndex TextNode."""
    metadata = _metadata_with_required_fields(
        metadata=result.metadata,
        chunk_id=result.id,
        resource_id=result.resource_id,
        user_id=result.user_id,
    )
    metadata["score"] = result.score
    return TextNode(id_=result.id, text=result.text or "", extra_info=metadata)


def node_with_score_to_chunk(node_with_score: NodeWithScore) -> RetrievalChunk:
    """Map a LlamaIndex NodeWithScore back to the stable MKC RetrievalChunk."""
    return node_to_retrieval_chunk(
        node_with_score.node,
        score=0.0 if node_with_score.score is None else float(node_with_score.score),
    )


def node_to_retrieval_chunk(node: BaseNode, score: float | None = None) -> RetrievalChunk:
    """Map a LlamaIndex node back to the stable MKC RetrievalChunk."""
    metadata = _normalize_metadata(dict(node.metadata or {}))
    chunk_id = str(metadata.get("chunk_id") or node.node_id or "")
    resource_id = str(metadata.get("resource_id") or "")
    resolved_score = _resolve_score(score, metadata)
    return RetrievalChunk(
        chunk_id=chunk_id,
        resource_id=resource_id,
        text=node.get_content() or "",
        score=resolved_score,
        metadata=metadata,
    )


def _metadata_with_required_fields(
    *,
    metadata: dict[str, Any] | None,
    chunk_id: str,
    resource_id: str,
    user_id: str,
) -> dict[str, Any]:
    normalized = _normalize_metadata(dict(metadata or {}))
    normalized["chunk_id"] = chunk_id
    normalized["resource_id"] = resource_id
    normalized["user_id"] = user_id
    return normalized


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if "chunk_id" not in metadata and "id" in metadata:
        metadata["chunk_id"] = metadata["id"]
    if "resource_type" not in metadata and "source_type" in metadata:
        metadata["resource_type"] = metadata["source_type"]
    if "source_type" not in metadata and "resource_type" in metadata:
        metadata["source_type"] = metadata["resource_type"]
    if "timestamp_start" not in metadata and "start_sec" in metadata:
        metadata["timestamp_start"] = metadata["start_sec"]
    if "timestamp_end" not in metadata and "end_sec" in metadata:
        metadata["timestamp_end"] = metadata["end_sec"]
    if "start_sec" not in metadata and "timestamp_start" in metadata:
        metadata["start_sec"] = metadata["timestamp_start"]
    if "end_sec" not in metadata and "timestamp_end" in metadata:
        metadata["end_sec"] = metadata["timestamp_end"]
    return metadata


def _resolve_score(score: float | None, metadata: dict[str, Any]) -> float:
    if score is not None:
        return float(score)
    raw_score = metadata.get("score")
    if raw_score is None or raw_score == "":
        return 0.0
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0

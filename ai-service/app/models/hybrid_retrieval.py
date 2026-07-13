from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SearchSource = Literal["bm25", "vector", "rerank"]


class HybridRetrievalRequest(BaseModel):
    """Request body for the hybrid retrieval endpoint.

    Only ``question`` and ``resource_ids`` are required; every tuning
    parameter is optional and falls back to the ``hybrid_retrieval`` config
    section when ``None``. Unknown fields are ignored for forward-compat.
    """

    model_config = ConfigDict(extra="ignore")

    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(..., min_length=1, max_length=128)
    resource_ids: list[str] = Field(..., min_length=1, max_length=100)

    # Optional runtime overrides; ``None`` resolves to config defaults.
    bm25_weight: float | None = Field(default=None, ge=0.0)
    vector_weight: float | None = Field(default=None, ge=0.0)
    rrf_k: int | None = Field(default=None, ge=1)
    rerank_top_n: int | None = Field(default=None, ge=1, le=100)
    final_top_k: int | None = Field(default=None, ge=1, le=100)
    score_threshold: float | None = Field(default=None)
    timeout_ms: int | None = Field(default=None, ge=1, le=10000)

    @field_validator("resource_ids")
    @classmethod
    def _resource_ids_non_empty(cls, value: list[str]) -> list[str]:
        if any(not isinstance(rid, str) or not rid.strip() for rid in value):
            raise ValueError("resource_ids must contain non-empty strings")
        return value


class SearchResult(BaseModel):
    """A single candidate produced by a retrieval path or the reranker.

    ``source`` records which stage produced the score currently carried:
    ``bm25`` / ``vector`` for the raw paths, ``rrf`` after fusion, and
    ``rerank`` after cross-encoder reranking.
    """

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    resource_id: str
    user_id: str = ""
    text: str = ""
    score: float = 0.0
    source: SearchSource = "vector"
    metadata: dict = Field(default_factory=dict)


class FusionStats(BaseModel):
    """Statistics describing the RRF fusion step."""

    bm25_count: int = 0
    vector_count: int = 0
    fused_count: int = 0


class HybridRetrievalResult(BaseModel):
    """Response body for the hybrid retrieval endpoint."""

    chunks: list[SearchResult] = Field(default_factory=list)
    fusion: FusionStats = Field(default_factory=FusionStats)
    degraded: bool = False
    elapsed_ms: int = 0

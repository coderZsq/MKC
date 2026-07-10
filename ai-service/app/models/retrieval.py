from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RetrievalRequest(BaseModel):
    """Request body for the retrieval endpoint.

    Unknown fields are ignored to stay forward-compatible with extra metadata.
    """

    model_config = ConfigDict(extra="ignore")

    question: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    resource_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=100)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_context_tokens: int | None = Field(default=None, ge=1)


class RetrievalChunk(BaseModel):
    """A single relevant chunk returned by the retrieval service."""

    chunk_id: str
    resource_id: str
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Response body for the retrieval endpoint."""

    chunks: list[RetrievalChunk]
    prompt: str
    context_token_count: int = 0

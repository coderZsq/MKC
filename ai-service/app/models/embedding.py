from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChunkInput(BaseModel):
    """A lightweight chunk reference used as input to the embedding service."""

    id: str
    resource_id: str
    text: str = ""


class Embedding(BaseModel):
    """A dense vector embedding produced for a single text chunk."""

    chunk_id: str
    resource_id: str
    vector: list[float]
    model: str
    dimensions: int = Field(..., gt=0)


class EmbeddingRequest(BaseModel):
    """Request body for the embedding endpoint.

    Unknown fields are ignored to stay forward-compatible with extra metadata.
    """

    model_config = ConfigDict(extra="ignore")

    chunks: list[ChunkInput] = Field(default_factory=list)


class EmbeddingResponse(BaseModel):
    """Response body for the embedding endpoint."""

    embeddings: list[Embedding]

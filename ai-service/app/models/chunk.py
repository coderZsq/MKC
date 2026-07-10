from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Chunk(BaseModel):
    """A text chunk produced by a chunking strategy.

    Chunks preserve the original resource identifier and any source metadata
    (page, timestamp range, etc.) so downstream embedding and retrieval can
    trace results back to the source document.
    """

    id: str
    resource_id: str
    index: int = Field(..., ge=0)
    text: str
    start_pos: int = Field(..., ge=0)
    end_pos: int = Field(..., ge=0)
    metadata: dict = Field(default_factory=dict)
    token_count: int = Field(..., ge=0)


class ChunkRequest(BaseModel):
    """Request body for the text chunking endpoint.

    Unknown fields are ignored so the endpoint stays forward-compatible with
    extra caller-provided metadata.
    """

    model_config = ConfigDict(extra="ignore")

    resource_id: str = ""
    text: str = ""
    metadata: dict = Field(default_factory=dict)
    strategy: str | None = None

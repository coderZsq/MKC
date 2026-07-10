from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class VectorRecord(BaseModel):
    """A single vector record stored in the vector database."""

    model_config = ConfigDict(extra="ignore")

    id: str
    resource_id: str
    user_id: str = ""
    text: str = ""
    vector: list[float]
    metadata: dict = Field(default_factory=dict)
    created_at: int = Field(
        default_factory=lambda: int(datetime.now(UTC).timestamp()),
    )


class VectorSearchRequest(BaseModel):
    """Request body for similarity search over stored vectors."""

    model_config = ConfigDict(extra="ignore")

    vector: list[float]
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, str] = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    """A single match returned by vector similarity search."""

    id: str
    resource_id: str
    user_id: str = ""
    text: str = ""
    metadata: dict
    score: float
    created_at: int = 0


class VectorUpsertRequest(BaseModel):
    """Request body for upserting a batch of vector records."""

    model_config = ConfigDict(extra="ignore")

    records: list[VectorRecord] = Field(default_factory=list)


class VectorDeleteRequest(BaseModel):
    """Request body for deleting vectors that belong to a resource."""

    model_config = ConfigDict(extra="ignore")

    resource_id: str
    user_id: str | None = None


class VectorUpsertResponse(BaseModel):
    """Response body after a successful upsert."""

    upserted_count: int


class VectorSearchResponse(BaseModel):
    """Response body for a vector search."""

    results: list[VectorSearchResult]

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A traceable source citation mapped from an answer footnote marker."""

    index: int = Field(..., ge=1)
    chunk_id: str
    resource_id: str
    resource_type: Literal["audio", "pdf"] = "pdf"
    page: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    score: float
    snippet: str | None = None


class CitationResult(BaseModel):
    """Citation post-processing result."""

    answer: str
    citations: list[Citation]

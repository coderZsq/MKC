from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SectionSummary(BaseModel):
    title: str
    summary: str = ""
    content: str = Field(default="", exclude=True)
    page_range: list[int] | None = None
    timestamp_range: list[float] | None = None


class SummaryResult(BaseModel):
    resource_id: str
    full_summary: str = ""
    sections: list[SectionSummary] = Field(default_factory=list)
    model: str
    tokens: int = 0
    fallback: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SummarizeRequest(BaseModel):
    types: list[str] = Field(default_factory=lambda: ["full", "section"])
    source_type: str = Field(default="pdf", pattern="^(pdf|audio|media)$")
    content: str = ""
    parsed: dict | None = None
    srt_segments: list[dict] | None = None
    task_id: str | None = None

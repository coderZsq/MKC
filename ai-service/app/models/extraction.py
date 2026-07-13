from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

EntityType = Literal["PERSON", "ORG", "DATE", "LOC", "GPE", "MISC"]
ExtractionSource = Literal["llm", "rule"]


class ExtractTagsRequest(BaseModel):
    content: str = ""
    source_type: str = Field(default="pdf", pattern="^(pdf|audio|media)$")
    task_id: str | None = None


class Tag(BaseModel):
    tag: str
    source: ExtractionSource = "llm"


class Entity(BaseModel):
    entity: str
    type: EntityType
    mention: str
    source: ExtractionSource = "llm"


class ExtractionResult(BaseModel):
    tags: list[str] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    source: ExtractionSource = "llm"


class ExtractionResponse(BaseModel):
    resource_id: str
    tags: list[Tag] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    source: ExtractionSource = "llm"
    fallback: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

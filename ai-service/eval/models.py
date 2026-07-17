from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Difficulty = Literal["easy", "medium", "hard"]


class ExpectedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: str = Field(min_length=1)
    chunk_id: str | None = Field(default=None, min_length=1)
    page: int | None = Field(default=None, ge=1)
    start_sec: float | None = Field(default=None, ge=0)
    end_sec: float | None = Field(default=None, ge=0)
    quote_hint: str | None = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_locator(self) -> ExpectedCitation:
        has_page = self.page is not None
        has_time = self.start_sec is not None or self.end_sec is not None
        has_chunk = self.chunk_id is not None
        if not (has_page or has_time or has_chunk):
            raise ValueError("citation must include page, time range, or chunk_id")
        if has_time and (self.start_sec is None or self.end_sec is None):
            raise ValueError("time citation must include both start_sec and end_sec")
        if (
            self.start_sec is not None
            and self.end_sec is not None
            and self.end_sec <= self.start_sec
        ):
            raise ValueError("end_sec must be greater than start_sec")
        return self


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^rag-[a-z0-9-]+-\d{3}$")
    question: str = Field(min_length=1, max_length=500)
    expected_answer: str = Field(min_length=1, max_length=1200)
    resource_ids: list[str] = Field(min_length=1)
    expected_citations: list[ExpectedCitation] = Field(default_factory=list)
    tags: list[str] = Field(min_length=1)
    difficulty: Difficulty

    @model_validator(mode="after")
    def validate_case(self) -> EvalCase:
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ValueError("resource_ids must be unique")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("tags must be unique")
        if "no_answer" in self.tags and self.expected_citations:
            raise ValueError("no_answer cases must not define expected_citations")
        citation_resource_ids = {citation.resource_id for citation in self.expected_citations}
        unknown_resource_ids = citation_resource_ids.difference(self.resource_ids)
        if unknown_resource_ids:
            raise ValueError("expected_citations resource_id must be listed in resource_ids")
        return self

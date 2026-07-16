from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.qa import ChatMessage, format_sse_event

AgentIntent = Literal["summarize", "qa", "compare", "generate"]


class AgentRunRequest(BaseModel):
    """Request body for the Agent workflow SSE endpoint."""

    model_config = ConfigDict(extra="ignore")

    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str = Field(..., min_length=1)
    message_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    resource_ids: list[str] = Field(default_factory=list, max_length=100)
    history: list[ChatMessage] = Field(default_factory=list)
    intent: AgentIntent | None = None
    enable_web_search: bool = True
    top_k: int | None = Field(default=None, ge=1, le=100)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    max_context_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=2048, gt=0)

    @field_validator("resource_ids")
    @classmethod
    def _resource_ids_non_empty(cls, value: list[str]) -> list[str]:
        if any(not isinstance(rid, str) or not rid.strip() for rid in value):
            raise ValueError("resource_ids must contain non-empty strings")
        return value


class AgentStreamEvent(BaseModel):
    """A single typed event emitted by the Agent stream."""

    event_type: str = Field(..., min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)

    def format_sse(self) -> str:
        """Render this event as an SSE payload."""
        return format_sse_event(self.event_type, self.data)

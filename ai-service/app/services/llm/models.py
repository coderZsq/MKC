from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    """A single message in an LLM chat conversation."""

    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class LLMRequest(BaseModel):
    """Request body for a chat completion call.

    Unknown fields are ignored so callers can include forward-compatible metadata.
    """

    model_config = ConfigDict(extra="ignore")

    messages: list[Message] = Field(..., min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)


class Usage(BaseModel):
    """Token usage reported by an LLM provider."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Non-streaming response from an LLM provider."""

    content: str
    reasoning: str | None = None
    model: str
    finish_reason: str = "stop"
    usage: Usage


class LLMStreamChunk(BaseModel):
    """A single incremental chunk from a streaming completion."""

    delta: str
    reasoning_delta: str | None = None
    finish_reason: str | None = None

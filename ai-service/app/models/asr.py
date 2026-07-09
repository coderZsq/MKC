from typing import Any

from pydantic import BaseModel, Field


class AsrSegment(BaseModel):
    start: float = Field(..., ge=0)
    end: float = Field(..., ge=0)
    text: str
    confidence: float | None = None


class AsrTaskRequest(BaseModel):
    task_id: str
    resource_id: str
    audio_url: str
    language: str | None = "zh"
    model: str | None = "small"


class AsrTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str = "ASR task queued"


class AsrResult(BaseModel):
    task_id: str
    resource_id: str
    segments: list[AsrSegment]
    text: str
    duration: float | None = None
    subtitle_url: str | None = None


class AsrProgress(BaseModel):
    progress: int = Field(..., ge=0, le=100)
    status: str


class AsrStatusUpdate(BaseModel):
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None

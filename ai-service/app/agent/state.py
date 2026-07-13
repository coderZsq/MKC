from __future__ import annotations

from typing import Any, TypedDict

from app.models.qa import ChatMessage
from app.models.retrieval import RetrievalChunk


class AgentState(TypedDict, total=False):
    """Mutable workflow state shared by LangGraph nodes."""

    messages: list[ChatMessage]
    intent: str
    question: str
    conversation_id: str
    message_id: str
    user_id: str
    resource_ids: list[str]
    retrieved_chunks: list[RetrievalChunk]
    draft_answer: str
    final_answer: str
    citations: list[dict[str, Any]]
    iterations: int
    max_iterations: int
    validation_passed: bool
    low_confidence: bool
    error: str | None
    top_k: int | None
    score_threshold: float | None
    max_context_tokens: int | None
    temperature: float | None
    max_tokens: int | None
    enable_web_search: bool
    memory_context: str


REQUIRED_AGENT_STATE_FIELDS = {
    "messages",
    "intent",
    "retrieved_chunks",
    "draft_answer",
    "citations",
    "iterations",
}

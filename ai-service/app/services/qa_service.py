from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.core.exceptions import (
    APIException,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.models.qa import QARequest, QAStreamEvent, format_sse_event
from app.models.retrieval import RetrievalRequest
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMRequest, Message
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class QAService:
    """Orchestrates retrieval, prompt assembly, and LLM streaming for Q&A."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
    ) -> None:
        self._retrieval = retrieval_service
        self._llm = llm_client

    async def stream_answer(self, request: QARequest) -> AsyncIterator[QAStreamEvent]:
        """Yield SSE events for a single question.

        The stream yields ``chunk`` events for incremental LLM output, followed by
        ``citation`` events for retrieved sources, and finally ``done`` or
        ``error``.
        """
        try:
            retrieval_kwargs: dict[str, Any] = {
                "question": request.question,
                "user_id": request.user_id,
                "resource_ids": request.resource_ids,
                "max_context_tokens": request.max_context_tokens,
            }
            if request.top_k is not None:
                retrieval_kwargs["top_k"] = request.top_k
            if request.score_threshold is not None:
                retrieval_kwargs["score_threshold"] = request.score_threshold
            retrieval_result = self._retrieval.retrieve(RetrievalRequest(**retrieval_kwargs))
        except APIException as exc:
            yield self._error_event(request, exc.code, exc.message)
            return
        except Exception:
            logger.exception("Retrieval failed for question %s", request.question)
            yield self._error_event(request, "RETRIEVAL_UNAVAILABLE", "检索不可用")
            return

        messages = self._build_messages(request, retrieval_result.prompt)
        llm_request = LLMRequest(
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2048,
        )

        try:
            index = 0
            async for chunk in self._llm.stream_complete(llm_request):
                if chunk.delta:
                    yield self._chunk_event(request, chunk.delta, index)
                    index += 1
                if chunk.finish_reason == "error":
                    yield self._error_event(request, "LLM_TIMEOUT", "生成超时")
                    return
                if chunk.finish_reason == "stop":
                    break
            for citation_chunk in retrieval_result.chunks:
                yield self._citation_event(request, citation_chunk)
            yield self._done_event(request)
        except (LLMUnavailableError, LLMTimeoutError) as exc:
            logger.warning("LLM stream failed: %s", exc.code)
            yield self._error_event(request, exc.code, exc.message)
        except Exception:
            logger.exception("LLM streaming failed for question %s", request.question)
            yield self._error_event(request, "LLM_STREAM_ERROR", "流式生成失败")

    def _build_messages(self, request: QARequest, prompt: str) -> list[dict[str, str]]:
        """Assemble the message list from history and the retrieved prompt."""
        messages: list[dict[str, str]] = []
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _chunk_event(self, request: QARequest, delta: str, index: int) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="chunk",
            data={
                "message_id": request.message_id,
                "conversation_id": request.conversation_id,
                "delta": delta,
                "index": index,
            },
        )

    def _citation_event(self, request: QARequest, chunk: Any) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="citation",
            data={
                "message_id": request.message_id,
                "resource_id": chunk.resource_id,
                "score": chunk.score,
                "metadata": chunk.metadata,
            },
        )

    def _done_event(self, request: QARequest) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="done",
            data={"message_id": request.message_id, "finish_reason": "stop"},
        )

    def _error_event(self, request: QARequest, error_code: str, message: str) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="error",
            data={
                "message_id": request.message_id,
                "conversation_id": request.conversation_id,
                "error_code": error_code,
                "message": message,
            },
        )


async def format_qa_stream(
    stream: AsyncIterator[QAStreamEvent],
) -> AsyncIterator[str]:
    """Convert QA stream events into SSE formatted strings."""
    async for event in stream:
        yield format_sse_event(event.event_type, event.data)

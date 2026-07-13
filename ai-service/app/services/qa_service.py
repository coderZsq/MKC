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
from app.models.retrieval import RetrievalChunk, RetrievalRequest
from app.services.citation_service import CitationService, citation_to_event_data
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMRequest, Message
from app.services.memory import MemoryService
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class QAService:
    """Orchestrates retrieval, prompt assembly, and LLM streaming for Q&A."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
        citation_service: CitationService | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self._retrieval = retrieval_service
        self._llm = llm_client
        self._citation = citation_service
        self._memory = memory_service

    async def stream_answer(self, request: QARequest) -> AsyncIterator[QAStreamEvent]:
        """Yield SSE events for a single question.

        The stream yields ``chunk`` events for incremental LLM output,
        ``reasoning`` events for model chain-of-thought (when provided by the
        LLM), ``citation`` events for retrieved sources, and finally ``done`` or
        ``error``.
        """
        memory_context = ""
        if self._memory is not None:
            memory_context = await self._memory.load_context(
                request.user_id, request.conversation_id, request.question
            )

        retrieval_result: Any | None = None
        prompt = request.question
        if request.resource_ids:
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
                prompt = retrieval_result.prompt
            except APIException as exc:
                yield self._error_event(request, exc.code, exc.message)
                return
            except Exception:
                logger.exception("Retrieval failed for question %s", request.question)
                yield self._error_event(request, "RETRIEVAL_UNAVAILABLE", "检索不可用")
                return

        messages = self._build_messages(request, prompt, memory_context=memory_context)
        llm_request = LLMRequest(
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2048,
        )

        try:
            chunk_index = 0
            reasoning_index = 0
            answer_parts: list[str] = []
            reasoning_parts: list[str] = []
            async for chunk in self._llm.stream_complete(llm_request):
                if chunk.delta:
                    answer_parts.append(chunk.delta)
                    yield self._chunk_event(request, chunk.delta, chunk_index)
                    chunk_index += 1
                if chunk.reasoning_delta:
                    reasoning_parts.append(chunk.reasoning_delta)
                    yield self._reasoning_event(request, chunk.reasoning_delta, reasoning_index)
                    reasoning_index += 1
                if chunk.finish_reason == "error":
                    yield self._error_event(request, "LLM_TIMEOUT", "生成超时")
                    return
                if chunk.finish_reason == "stop":
                    break
            citations = self._build_citations(
                request,
                "".join(answer_parts),
                retrieval_result.chunks if retrieval_result is not None else [],
            )
            for citation in citations:
                yield self._citation_event(request, citation)
            yield self._done_event(request, len(citations))
            if self._memory is not None:
                await self._memory.save_turn(
                    request.user_id,
                    request.conversation_id,
                    request.question,
                    "".join(answer_parts),
                    reasoning="".join(reasoning_parts),
                )
        except (LLMUnavailableError, LLMTimeoutError) as exc:
            logger.warning("LLM stream failed: %s", exc.code)
            yield self._error_event(request, exc.code, exc.message)
        except Exception:
            logger.exception("LLM streaming failed for question %s", request.question)
            yield self._error_event(request, "LLM_STREAM_ERROR", "流式生成失败")

    def _build_messages(
        self, request: QARequest, prompt: str, *, memory_context: str = ""
    ) -> list[dict[str, str]]:
        """Assemble the message list from memory context, history, and the retrieved prompt."""
        messages: list[dict[str, str]] = []
        if memory_context:
            messages.append({"role": "system", "content": memory_context})
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

    def _reasoning_event(self, request: QARequest, delta: str, index: int) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="reasoning",
            data={
                "message_id": request.message_id,
                "conversation_id": request.conversation_id,
                "delta": delta,
                "index": index,
            },
        )

    def _build_citations(
        self, request: QARequest, answer: str, chunks: list[RetrievalChunk]
    ) -> list[dict[str, Any]]:
        if self._citation is None or not chunks:
            return []
        result = self._citation.build_citations(
            answer=answer,
            chunks=chunks,
            authorized_resource_ids=set(request.resource_ids),
        )
        return [citation_to_event_data(citation) for citation in result.citations]

    def _citation_event(self, request: QARequest, citation: dict[str, Any]) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="citation",
            data={"message_id": request.message_id, **citation},
        )

    def _done_event(self, request: QARequest, citation_count: int = 0) -> QAStreamEvent:
        return QAStreamEvent(
            event_type="done",
            data={
                "message_id": request.message_id,
                "finish_reason": "stop",
                "citation_count": citation_count,
            },
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

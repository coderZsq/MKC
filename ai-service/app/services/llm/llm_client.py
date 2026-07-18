from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from collections.abc import AsyncGenerator, AsyncIterator, Iterator

from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.exceptions import APIException, LLMStreamError, LLMTimeoutError, LLMUnavailableError
from app.observability.llm import (
    LLMGenerationEvent,
    LLMObserver,
    NoopObserver,
    safe_record_error,
    safe_record_generation,
)
from app.observability.llm.observer import LLMObserverConfig
from app.observability.tracing import get_trace_id
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.config import LLMConfig
from app.services.llm.models import LLMRequest, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified entry point for LLM completion and streaming completion."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        fallback_provider: BaseLLMProvider | None = None,
        config: LLMConfig | None = None,
        observer: LLMObserver | None = None,
        observer_config: LLMObserverConfig | None = None,
    ) -> None:
        self._provider = provider
        self._fallback_provider = fallback_provider
        self._config = config
        self._observer = observer or NoopObserver()
        self._observer_config = observer_config or LLMObserverConfig()

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a complete response, retrying and falling back when configured."""
        try:
            return self._complete_with_provider(self._provider, request)
        except (LLMUnavailableError, LLMTimeoutError) as exc:
            if self._fallback_provider is None:
                raise
            logger.warning("Primary LLM provider failed (%s), trying fallback model", exc.code)
            return self._complete_with_provider(self._fallback_provider, request)

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """Yield incremental chunks from the primary provider.

        If the stream is interrupted, a final chunk with ``finish_reason="error"``
        is yielded so callers can still use any content already received.
        """
        started_at = time.monotonic()
        answer_parts: list[str] = []
        status = "success"
        error_code: str | None = None
        try:
            async for chunk in self._provider.stream_complete(request):
                answer_parts.append(chunk.delta)
                if chunk.finish_reason == "error":
                    status = "error"
                    error_code = "LLM_STREAM_ERROR"
                yield chunk
        except (LLMUnavailableError, LLMTimeoutError, LLMStreamError) as exc:
            logger.warning("LLM stream failed: %s", exc.code)
            status = "error"
            error_code = exc.code
            yield LLMStreamChunk(delta="", finish_reason="error")
        finally:
            event = self._build_event(
                request=request,
                response=None,
                completion="".join(answer_parts),
                latency_ms=_latency_ms(started_at),
                status=status,
                error_code=error_code,
            )
            if status == "error":
                safe_record_error(self._observer, event)
            else:
                safe_record_generation(self._observer, event)

    def _complete_with_provider(
        self, provider: BaseLLMProvider, request: LLMRequest
    ) -> LLMResponse:
        max_retries = self._config.max_retries if self._config else 3
        started_at = time.monotonic()
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type((LLMUnavailableError, LLMTimeoutError)),
                reraise=True,
            ):
                with attempt:
                    response = provider.complete(request)
                    safe_record_generation(
                        self._observer,
                        self._build_event(
                            request=request,
                            response=response,
                            completion=response.content,
                            latency_ms=_latency_ms(started_at),
                            status="success",
                        ),
                    )
                    return response
        except (LLMUnavailableError, LLMTimeoutError) as exc:
            safe_record_error(
                self._observer,
                self._build_event(
                    request=request,
                    response=None,
                    completion="",
                    latency_ms=_latency_ms(started_at),
                    status="error",
                    error_code=exc.code,
                ),
            )
            raise
        except APIException as exc:
            safe_record_error(
                self._observer,
                self._build_event(
                    request=request,
                    response=None,
                    completion="",
                    latency_ms=_latency_ms(started_at),
                    status="error",
                    error_code=exc.code,
                ),
            )
            raise
        except Exception as exc:
            logger.exception("LLM provider failed after retries")
            safe_record_error(
                self._observer,
                self._build_event(
                    request=request,
                    response=None,
                    completion="",
                    latency_ms=_latency_ms(started_at),
                    status="error",
                    error_code="LLM_UNAVAILABLE",
                ),
            )
            raise LLMUnavailableError() from exc
        # Retrying guarantees either a return or a raise, so this is unreachable.
        raise LLMUnavailableError()

    def _build_event(
        self,
        *,
        request: LLMRequest,
        response: LLMResponse | None,
        completion: str,
        latency_ms: int,
        status: str,
        error_code: str | None = None,
    ) -> LLMGenerationEvent:
        usage = response.usage if response is not None else None
        return LLMGenerationEvent(
            trace_id=get_trace_id(),
            prompt_version=self._observer_config.prompt_version,
            provider=self._config.provider if self._config else "unknown",
            model=(
                response.model
                if response is not None
                else (self._config.model if self._config else "unknown")
            ),
            prompt=_request_prompt(request),
            completion=completion,
            latency_ms=latency_ms,
            input_tokens=usage.prompt_tokens if usage is not None else 0,
            output_tokens=usage.completion_tokens if usage is not None else 0,
            total_tokens=usage.total_tokens if usage is not None else 0,
            status=status,
            error_code=error_code,
        )


def _request_prompt(request: LLMRequest) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in request.messages)


def _latency_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


async def format_sse_stream(
    stream: AsyncIterator[LLMStreamChunk],
) -> AsyncIterator[str]:
    """Convert a stream of chunks into Server-Sent Events text."""
    async for chunk in stream:
        data = chunk.model_dump_json(exclude_none=True)
        yield f"event: message\ndata: {data}\n\n"
    yield 'event: done\ndata: {"finish_reason":"stop"}\n\n'


def sync_format_sse_stream(stream: AsyncIterator[str]) -> Iterator[str]:
    """Run an async SSE iterator incrementally in a synchronous context.

    Flask WSGI views run without an event loop, so a new loop is created and
    driven directly. When called from an already running loop (e.g. async tests),
    the iterator is driven in a background thread so both contexts remain
    non-blocking.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Standard Flask path: no event loop is running yet.
        loop = asyncio.new_event_loop()
        agen = stream.__aiter__()

        async def _anext() -> str:
            return await agen.__anext__()

        try:
            while True:
                try:
                    yield loop.run_until_complete(_anext())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()
        return

    # Already inside a running loop (e.g. async test runner). Drive the iterator
    # in a dedicated background thread and relay chunks through a queue so the
    # foreground loop is not blocked.
    _sentinel = object()
    q: queue.Queue[str | BaseException | object] = queue.Queue()

    async def _consume() -> None:
        try:
            async for chunk in stream:
                q.put(chunk)
        except BaseException as exc:
            q.put(exc)
        finally:
            q.put(_sentinel)

    def _run_loop() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_consume())
        finally:
            loop.close()

    threading.Thread(target=_run_loop, daemon=True).start()
    while True:
        item = q.get()
        if item is _sentinel:
            break
        if isinstance(item, BaseException):
            raise item
        assert isinstance(item, str)
        yield item

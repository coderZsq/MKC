from __future__ import annotations

import asyncio
import logging
import queue
import threading
from collections.abc import AsyncGenerator, AsyncIterator, Iterator

from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.exceptions import APIException, LLMStreamError, LLMTimeoutError, LLMUnavailableError
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
    ) -> None:
        self._provider = provider
        self._fallback_provider = fallback_provider
        self._config = config

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
        try:
            async for chunk in self._provider.stream_complete(request):
                yield chunk
        except (LLMUnavailableError, LLMTimeoutError, LLMStreamError) as exc:
            logger.warning("LLM stream failed: %s", exc.code)
            yield LLMStreamChunk(delta="", finish_reason="error")

    def _complete_with_provider(
        self, provider: BaseLLMProvider, request: LLMRequest
    ) -> LLMResponse:
        max_retries = self._config.max_retries if self._config else 3
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type((LLMUnavailableError, LLMTimeoutError)),
                reraise=True,
            ):
                with attempt:
                    return provider.complete(request)
        except (LLMUnavailableError, LLMTimeoutError):
            raise
        except APIException:
            raise
        except Exception as exc:
            logger.exception("LLM provider failed after retries")
            raise LLMUnavailableError() from exc
        # Retrying guarantees either a return or a raise, so this is unreachable.
        raise LLMUnavailableError()


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

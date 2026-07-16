from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any, cast

from pydantic import ValidationError as PydanticValidationError
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.agent.tools.base_search_provider import BaseSearchProvider
from app.agent.tools.search_providers import build_search_provider
from app.agent.tools.web_search_config import WebSearchConfig, build_web_search_config
from app.models.web_search import WebSearchRequest, WebSearchResponse, WebSearchResult
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMRequest, Message

logger = logging.getLogger(__name__)

try:
    from langchain_core.tools import tool as _lc_tool
except ModuleNotFoundError:

    def _lc_tool(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def _decorate(func: Callable[..., Any]) -> Callable[..., Any]:
            cast(Any, func).name = name
            return func

        return _decorate


class RateLimitExceededError(Exception):
    """Raised when web search calls exceed the configured local rate limit."""


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._calls: deque[float] = deque()

    def acquire(self) -> None:
        if self._limit <= 0:
            raise RateLimitExceededError("web search disabled by rate limit")
        now = time.monotonic()
        while self._calls and now - self._calls[0] >= self._window_seconds:
            self._calls.popleft()
        if len(self._calls) >= self._limit:
            raise RateLimitExceededError("web search rate limit exceeded")
        self._calls.append(now)


class WebSearchTool:
    """Web search tool used by Agent nodes and the internal test endpoint."""

    def __init__(
        self,
        provider: BaseSearchProvider | None = None,
        config: WebSearchConfig | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self._config = config or build_web_search_config()
        self._provider = provider or build_search_provider(self._config)
        self._rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            self._config.rate_limit_per_minute
        )

        async def _web_search(query: str, top_k: int = self._config.top_k) -> dict[str, Any]:
            """Search the web when knowledge-base context is insufficient."""
            response = await self.invoke(query=query, top_k=top_k)
            return response.model_dump()

        self.web_search = _lc_tool("web_search")(_web_search)

    async def invoke(self, query: str, top_k: int | None = None) -> WebSearchResponse:
        request = WebSearchRequest(
            query=query.strip(),
            top_k=min(top_k or self._config.top_k, self._config.max_top_k),
        )
        try:
            self._rate_limiter.acquire()
            results = await self._search_with_retries(request)
        except PydanticValidationError:
            raise
        except Exception as exc:
            logger.warning("web search fallback: %s", exc)
            return WebSearchResponse(results=[], fallback=True)
        return WebSearchResponse(results=results, fallback=False)

    async def _search_with_retries(self, request: WebSearchRequest) -> list[WebSearchResult]:
        attempts = max(1, self._config.max_retries)
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self._config.retry_backoff_min,
                max=self._config.retry_backoff_max,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                return await self._provider.search(request)
        return []


async def summarize_and_inject(
    results: list[WebSearchResult],
    llm: LLMClient,
    *,
    complete: Callable[[LLMRequest], Any] | None = None,
) -> str:
    """Summarize web results as a separate "network source" context block."""
    if not results:
        return ""
    joined = "\n".join(f"- {r.title}: {r.snippet} ({r.url})" for r in results)
    request = LLMRequest(
        messages=[
            Message(
                role="user",
                content=f"请将以下网络搜索结果摘要为简洁信息，标注为「网络来源」：\n{joined}",
            )
        ],
        temperature=0.2,
        max_tokens=512,
    )
    complete_fn = complete or llm.complete
    response = complete_fn(request)
    if isinstance(response, Awaitable):
        response = await response
    content = getattr(response, "content", str(response))
    return f"【网络来源】{content}"

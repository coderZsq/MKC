from __future__ import annotations

import asyncio
from typing import Any

from app.agent.tools.base_search_provider import BaseSearchProvider
from app.agent.tools.search_providers import BingProvider, SerperProvider
from app.agent.tools.web_search_config import ProviderConfig, WebSearchConfig
from app.agent.tools.web_search_tool import (
    SlidingWindowRateLimiter,
    WebSearchTool,
    summarize_and_inject,
)
from app.models.web_search import WebSearchRequest, WebSearchResult
from app.services.llm.models import LLMResponse, Usage


class _Provider(BaseSearchProvider):
    def __init__(
        self,
        results: list[WebSearchResult] | None = None,
        raises: bool = False,
    ) -> None:
        self.results = results or []
        self.raises = raises
        self.requests: list[WebSearchRequest] = []

    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        self.requests.append(request)
        if self.raises:
            raise RuntimeError("search failed")
        return self.results[: request.top_k]

    def parse_response(self, raw: dict[str, Any], top_k: int) -> list[WebSearchResult]:
        return self.results[:top_k]


def _result(idx: int = 1) -> WebSearchResult:
    return WebSearchResult(
        title=f"Result {idx}",
        url=f"https://example.com/{idx}",
        snippet=f"Snippet {idx}",
    )


def test_web_search_returns_structured_results() -> None:
    # MKC-TC-S4-8-001: web_search returns title/url/snippet and source_type=web.
    provider = _Provider([_result(1), _result(2)])
    tool = WebSearchTool(provider=provider, config=WebSearchConfig(provider="mock"))

    response = asyncio.run(tool.invoke("latest LLM inference", top_k=5))

    assert response.source_type == "web"
    assert response.fallback is False
    assert response.results[0].title == "Result 1"


def test_top_k_is_capped_by_request_and_config() -> None:
    # MKC-TC-S4-8-002 and MKC-TC-S4-8-023: top_k controls count and max_top_k caps requests.
    provider = _Provider([_result(i) for i in range(20)])
    tool = WebSearchTool(
        provider=provider,
        config=WebSearchConfig(provider="mock", top_k=5, max_top_k=3),
    )

    response = asyncio.run(tool.invoke("query", top_k=99))

    assert len(response.results) == 3
    assert provider.requests[0].top_k == 3


def test_provider_failure_degrades_to_empty_results() -> None:
    # MKC-TC-S4-8-017 and MKC-TC-S4-8-018: failures do not block Agent flow.
    tool = WebSearchTool(
        provider=_Provider(raises=True),
        config=WebSearchConfig(provider="mock", max_retries=1),
    )

    response = asyncio.run(tool.invoke("query", top_k=5))

    assert response.results == []
    assert response.fallback is True


def test_rate_limit_degrades_to_empty_results() -> None:
    # MKC-TC-S4-8-019: local rate limit causes fallback.
    tool = WebSearchTool(
        provider=_Provider([_result()]),
        config=WebSearchConfig(provider="mock", rate_limit_per_minute=1),
        rate_limiter=SlidingWindowRateLimiter(limit=1, window_seconds=60),
    )

    first = asyncio.run(tool.invoke("query"))
    second = asyncio.run(tool.invoke("query"))

    assert first.fallback is False
    assert second.fallback is True
    assert second.results == []


def test_serper_parse_response_skips_invalid_items_and_truncates() -> None:
    # MKC-TC-S4-8-024 and MKC-TC-S4-8-032: parser skips bad items and truncates snippet.
    provider = SerperProvider(
        ProviderConfig(api_key="dummy", base_url="https://serper.test", timeout=1),
        WebSearchConfig(snippet_max_length=6),
    )

    results = provider.parse_response(
        {
            "organic": [
                {"title": "Good", "link": "https://example.com", "snippet": "abcdefghi"},
                {"title": "No URL"},
                "bad",
            ]
        },
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].snippet == "abcdef"


def test_bing_parse_response_maps_name_url_snippet() -> None:
    # MKC-TC-S4-8-030: Bing normalizes to the same WebSearchResult shape.
    provider = BingProvider(
        ProviderConfig(api_key="dummy", base_url="https://bing.test", timeout=1),
        WebSearchConfig(),
    )

    results = provider.parse_response(
        {"webPages": {"value": [{"name": "Bing", "url": "https://b.test", "snippet": "s"}]}},
        top_k=5,
    )

    assert results == [WebSearchResult(title="Bing", url="https://b.test", snippet="s")]


def test_summarize_and_inject_marks_network_source() -> None:
    # MKC-TC-S4-8-008 and MKC-TC-S4-8-009: web results become a separate network source block.
    def complete(_: Any) -> LLMResponse:
        return LLMResponse(
            content="外部信息摘要",
            model="mock",
            usage=Usage(),
        )

    summary = asyncio.run(
        summarize_and_inject([_result()], llm=None, complete=complete)  # type: ignore[arg-type]
    )

    assert summary == "【网络来源】外部信息摘要"

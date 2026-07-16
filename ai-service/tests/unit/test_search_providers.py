from __future__ import annotations

import asyncio

from app.agent.tools import search_providers
from app.agent.tools.search_providers import BingProvider, CurlSearchProvider, SerperProvider
from app.agent.tools.web_search_config import (
    ProviderConfig,
    WebSearchConfig,
    build_web_search_config,
)
from app.models.web_search import WebSearchRequest


def test_default_provider_is_curl() -> None:
    # User constraint: search defaults to curl.
    config = build_web_search_config({})

    assert config.provider == "curl"


def test_curl_provider_builds_duckduckgo_curl_request(monkeypatch) -> None:
    # MKC-TC-S4-8-001: default curl provider returns structured results.
    calls: list[list[str]] = []

    async def fake_curl(args: list[str]) -> dict:
        calls.append(args)
        return {
            "Heading": "Example",
            "AbstractText": "Search summary",
            "AbstractURL": "https://example.com",
        }

    monkeypatch.setattr(search_providers, "_curl_json", fake_curl)
    provider = CurlSearchProvider(
        ProviderConfig(base_url="https://api.duckduckgo.com/", timeout=7),
        WebSearchConfig(provider="curl"),
    )

    results = asyncio.run(provider.search(WebSearchRequest(query="hello world", top_k=1)))

    assert results[0].title == "Example"
    assert calls[0][0] == "curl"
    assert "--max-time" in calls[0]
    assert "hello+world" in calls[0][-1]


def test_serper_provider_request_uses_api_key_header(monkeypatch) -> None:
    # MKC-TC-S4-8-004: Serper request contains X-API-KEY and q/num payload.
    calls: list[list[str]] = []

    async def fake_curl(args: list[str]) -> dict:
        calls.append(args)
        return {"organic": [{"title": "T", "link": "https://t.test", "snippet": "S"}]}

    monkeypatch.setattr(search_providers, "_curl_json", fake_curl)
    provider = SerperProvider(
        ProviderConfig(api_key="serper-key", base_url="https://serper.test/search", timeout=5),
        WebSearchConfig(provider="serper"),
    )

    asyncio.run(provider.search(WebSearchRequest(query="query", top_k=3)))

    assert "X-API-KEY: serper-key" in calls[0]
    assert '{"q": "query", "num": 3}' in calls[0]


def test_bing_provider_request_uses_subscription_header(monkeypatch) -> None:
    # MKC-TC-S4-8-005: Bing request contains subscription key header.
    calls: list[list[str]] = []

    async def fake_curl(args: list[str]) -> dict:
        calls.append(args)
        return {"webPages": {"value": [{"name": "T", "url": "https://t.test", "snippet": "S"}]}}

    monkeypatch.setattr(search_providers, "_curl_json", fake_curl)
    provider = BingProvider(
        ProviderConfig(api_key="bing-key", base_url="https://bing.test/search", timeout=5),
        WebSearchConfig(provider="bing"),
    )

    asyncio.run(provider.search(WebSearchRequest(query="query", top_k=3)))

    assert "Ocp-Apim-Subscription-Key: bing-key" in calls[0]
    assert "count=3" in calls[0][4]

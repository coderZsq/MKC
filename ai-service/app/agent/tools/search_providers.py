from __future__ import annotations

import asyncio
import json
import urllib.parse
from typing import Any, cast

from app.agent.tools.base_search_provider import BaseSearchProvider
from app.agent.tools.web_search_config import ProviderConfig, WebSearchConfig
from app.core.exceptions import APIException
from app.models.web_search import WebSearchRequest, WebSearchResult


class WebSearchConfigError(APIException):
    def __init__(self, message: str = "Web Search 配置无效") -> None:
        super().__init__("WEB_SEARCH_CONFIG_ERROR", message, 500)


class CurlSearchProvider(BaseSearchProvider):
    """Default provider that shells out to curl.

    The default endpoint is DuckDuckGo's JSON endpoint because it does not need
    a local API key, which keeps development and CI deterministic.
    """

    def __init__(self, provider_config: ProviderConfig, config: WebSearchConfig) -> None:
        self._provider_config = provider_config
        self._config = config

    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        query = urllib.parse.urlencode(
            {"q": request.query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        )
        url = f"{self._provider_config.base_url.rstrip('/')}?{query}"
        raw = await _curl_json(
            ["curl", "-sS", "--max-time", str(self._provider_config.timeout), url]
        )
        return self.parse_response(raw, request.top_k)

    def parse_response(self, raw: dict[str, Any], top_k: int) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        abstract = str(raw.get("AbstractText") or "")
        abstract_url = str(raw.get("AbstractURL") or "")
        heading = str(raw.get("Heading") or "DuckDuckGo result")
        if abstract and abstract_url:
            results.append(
                WebSearchResult(
                    title=heading,
                    url=abstract_url,
                    snippet=_truncate(abstract, self._config.snippet_max_length),
                )
            )
        for item in _flatten_related_topics(raw.get("RelatedTopics", [])):
            if len(results) >= top_k:
                break
            text = str(item.get("Text") or "")
            first_url = str(item.get("FirstURL") or "")
            if not text or not first_url:
                continue
            results.append(
                WebSearchResult(
                    title=text.split(" - ", 1)[0][:80] or "DuckDuckGo result",
                    url=first_url,
                    snippet=_truncate(text, self._config.snippet_max_length),
                )
            )
        return results[:top_k]


class SerperProvider(BaseSearchProvider):
    def __init__(self, provider_config: ProviderConfig, config: WebSearchConfig) -> None:
        if not provider_config.api_key:
            raise WebSearchConfigError("SERPER_API_KEY 未配置")
        self._provider_config = provider_config
        self._config = config

    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        payload = json.dumps({"q": request.query, "num": request.top_k})
        raw = await _curl_json(
            [
                "curl",
                "-sS",
                "--max-time",
                str(self._provider_config.timeout),
                "-X",
                "POST",
                self._provider_config.base_url,
                "-H",
                "Content-Type: application/json",
                "-H",
                f"X-API-KEY: {self._provider_config.api_key}",
                "-d",
                payload,
            ]
        )
        return self.parse_response(raw, request.top_k)

    def parse_response(self, raw: dict[str, Any], top_k: int) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        for item in raw.get("organic", [])[:top_k]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "")
            url = str(item.get("link") or "")
            if not title or not url:
                continue
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=_truncate(
                        str(item.get("snippet") or ""), self._config.snippet_max_length
                    ),
                )
            )
        return results


class BingProvider(BaseSearchProvider):
    def __init__(self, provider_config: ProviderConfig, config: WebSearchConfig) -> None:
        if not provider_config.api_key:
            raise WebSearchConfigError("BING_API_KEY 未配置")
        self._provider_config = provider_config
        self._config = config

    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        query = urllib.parse.urlencode({"q": request.query, "count": request.top_k})
        url = f"{self._provider_config.base_url}?{query}"
        raw = await _curl_json(
            [
                "curl",
                "-sS",
                "--max-time",
                str(self._provider_config.timeout),
                url,
                "-H",
                f"Ocp-Apim-Subscription-Key: {self._provider_config.api_key}",
            ]
        )
        return self.parse_response(raw, request.top_k)

    def parse_response(self, raw: dict[str, Any], top_k: int) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        for item in raw.get("webPages", {}).get("value", [])[:top_k]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("name") or "")
            url = str(item.get("url") or "")
            if not title or not url:
                continue
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=_truncate(
                        str(item.get("snippet") or ""), self._config.snippet_max_length
                    ),
                )
            )
        return results


class MockSearchProvider(BaseSearchProvider):
    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        return self.parse_response({}, request.top_k)

    def parse_response(self, raw: dict[str, Any], top_k: int) -> list[WebSearchResult]:
        return [
            WebSearchResult(
                title="Mock web result",
                url="https://example.com/mock-web-result",
                snippet="Mock search result for local development and CI.",
            )
        ][:top_k]


def build_search_provider(config: WebSearchConfig) -> BaseSearchProvider:
    if config.provider == "curl":
        return CurlSearchProvider(config.curl, config)
    if config.provider == "serper":
        return SerperProvider(config.serper, config)
    if config.provider == "bing":
        return BingProvider(config.bing, config)
    if config.provider == "mock":
        return MockSearchProvider()
    raise WebSearchConfigError(f"不支持的 Web Search provider: {config.provider}")


async def _curl_json(args: list[str]) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        message = stderr.decode("utf-8", errors="ignore") or "curl request failed"
        raise RuntimeError(message)
    return cast(dict[str, Any], json.loads(stdout.decode("utf-8") or "{}"))


def _flatten_related_topics(items: list[Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if "Topics" in item and isinstance(item["Topics"], list):
            flattened.extend(_flatten_related_topics(item["Topics"]))
        else:
            flattened.append(item)
    return flattened


def _truncate(value: str, max_length: int) -> str:
    return value[:max_length] if max_length > 0 else value

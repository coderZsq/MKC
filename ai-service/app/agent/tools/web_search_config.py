from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str = ""
    base_url: str = ""
    timeout: float = 10.0


@dataclass(frozen=True)
class WebSearchConfig:
    provider: str = "curl"
    top_k: int = 5
    max_top_k: int = 10
    rate_limit_per_minute: int = 20
    max_retries: int = 2
    retry_backoff_min: float = 1.0
    retry_backoff_max: float = 5.0
    snippet_max_length: int = 200
    curl: ProviderConfig = ProviderConfig(
        base_url="https://api.duckduckgo.com/",
        timeout=10.0,
    )
    serper: ProviderConfig = ProviderConfig(
        base_url="https://google.serper.dev/search",
        timeout=10.0,
    )
    bing: ProviderConfig = ProviderConfig(
        base_url="https://api.bing.microsoft.com/v7.0/search",
        timeout=10.0,
    )


def build_web_search_config(raw: dict[str, Any] | None = None) -> WebSearchConfig:
    cfg = raw or {}
    return WebSearchConfig(
        provider=str(cfg.get("provider", "curl")).lower(),
        top_k=int(cfg.get("top_k", 5)),
        max_top_k=int(cfg.get("max_top_k", 10)),
        rate_limit_per_minute=int(cfg.get("rate_limit_per_minute", 20)),
        max_retries=int(cfg.get("max_retries", 2)),
        retry_backoff_min=float(cfg.get("retry_backoff_min", 1)),
        retry_backoff_max=float(cfg.get("retry_backoff_max", 5)),
        snippet_max_length=int(cfg.get("snippet_max_length", 200)),
        curl=_provider_config(
            cfg.get("curl", {}),
            default_base_url="https://api.duckduckgo.com/",
            default_timeout=10.0,
        ),
        serper=_provider_config(
            cfg.get("serper", {}),
            default_base_url="https://google.serper.dev/search",
            default_timeout=10.0,
            env_key="SERPER_API_KEY",
        ),
        bing=_provider_config(
            cfg.get("bing", {}),
            default_base_url="https://api.bing.microsoft.com/v7.0/search",
            default_timeout=10.0,
            env_key="BING_API_KEY",
        ),
    )


def _provider_config(
    raw: dict[str, Any] | None,
    *,
    default_base_url: str,
    default_timeout: float,
    env_key: str | None = None,
) -> ProviderConfig:
    cfg = raw or {}
    api_key = _resolve_env_value(str(cfg.get("api_key", "")))
    if env_key:
        api_key = os.environ.get(env_key, api_key)
    return ProviderConfig(
        api_key=api_key,
        base_url=str(cfg.get("base_url", default_base_url)),
        timeout=float(cfg.get("timeout", default_timeout)),
    )


def _resolve_env_value(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value

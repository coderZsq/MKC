from __future__ import annotations

import logging

from app.core.exceptions import EmbeddingAuthenticationError, EmbeddingProviderError
from app.services.embedding.config import EmbeddingConfig, build_embedding_config
from app.services.embedding.mock import MockEmbeddingProvider
from app.services.embedding.ollama import OllamaEmbeddingProvider
from app.services.embedding.openai import OpenAiEmbeddingProvider
from app.services.embedding.opensource import OpenSourceEmbeddingProvider
from app.services.embedding.provider import EmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.embedding.zhipu import ZhipuEmbeddingProvider

logger = logging.getLogger(__name__)

_API_KEY_PROVIDERS: frozenset[str] = frozenset({"zhipuai", "openai"})


def build_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """Build an embedding provider instance from the resolved configuration."""
    if config.provider == "zhipuai":
        _require_api_key(config, "ZhipuAI")
        return ZhipuEmbeddingProvider(config)
    if config.provider == "openai":
        _require_api_key(config, "OpenAI")
        return OpenAiEmbeddingProvider(config)
    if config.provider == "ollama":
        return OllamaEmbeddingProvider(config)
    if config.provider == "opensource":
        return OpenSourceEmbeddingProvider(config)
    if config.provider == "mock":
        return MockEmbeddingProvider(config)
    raise EmbeddingProviderError(f"不支持的 embedding provider: {config.provider}")


def build_embedding_service(config: EmbeddingConfig | None = None) -> EmbeddingService:
    """Build a fully configured ``EmbeddingService``."""
    cfg = config if config is not None else build_embedding_config()
    provider = build_embedding_provider(cfg)
    return EmbeddingService(provider=provider, config=cfg)


def validate_embedding_config(config: EmbeddingConfig | None = None) -> None:
    """Validate that the embedding configuration can be used at runtime.

    This is intended to be called during application startup so missing API keys
    for remote providers fail fast. Local providers (opensource, mock) do not
    require an API key, but the rest of the configuration is still validated.
    """
    cfg = config if config is not None else build_embedding_config()
    if cfg.provider in _API_KEY_PROVIDERS:
        _require_api_key(cfg, cfg.provider)


def _require_api_key(config: EmbeddingConfig, provider_name: str) -> None:
    if not config.api_key:
        logger.error("%s API key is missing; embedding service cannot start", provider_name)
        raise EmbeddingAuthenticationError(f"{provider_name} API key 缺失，无法启动 embedding 服务")

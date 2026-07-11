from __future__ import annotations

import logging

from app.core.exceptions import LLMAuthFailedError
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.config import LLMConfig, build_llm_config
from app.services.llm.kimi_provider import KimiProvider
from app.services.llm.llm_client import LLMClient
from app.services.llm.mock_provider import MockProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.zhipu_provider import ZhipuProvider

logger = logging.getLogger(__name__)

_API_KEY_PROVIDERS: frozenset[str] = frozenset({"zhipuai", "kimi"})


def build_llm_provider(config: LLMConfig) -> BaseLLMProvider:
    """Build an LLM provider instance from the resolved configuration."""
    if config.provider == "zhipuai":
        return ZhipuProvider(config)
    if config.provider == "kimi":
        return KimiProvider(config)
    if config.provider == "ollama":
        return OllamaProvider(config)
    if config.provider == "mock":
        return MockProvider(config)
    raise ValueError(f"不支持的 LLM provider: {config.provider}")


def build_llm_client(config: LLMConfig | None = None) -> LLMClient:
    """Build a fully configured ``LLMClient``."""
    cfg = config if config is not None else build_llm_config()
    provider = build_llm_provider(cfg)
    fallback_provider = None
    if cfg.fallback_model:
        fallback_cfg = LLMConfig(
            provider=cfg.provider,
            model=cfg.fallback_model,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
        )
        fallback_provider = build_llm_provider(fallback_cfg)
    return LLMClient(provider=provider, fallback_provider=fallback_provider, config=cfg)


def validate_llm_config(config: LLMConfig | None = None) -> None:
    """Validate that the LLM configuration can be used at runtime.

    Remote providers require an API key. Mock providers do not.
    """
    cfg = config if config is not None else build_llm_config()
    if cfg.provider in _API_KEY_PROVIDERS and not cfg.api_key:
        logger.error("%s API key is missing; LLM service cannot start", cfg.provider)
        raise LLMAuthFailedError(f"{cfg.provider} API key 缺失，无法启动 LLM 服务")

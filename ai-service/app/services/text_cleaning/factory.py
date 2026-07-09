from __future__ import annotations

import logging
from typing import Any

from app.clients.llm_client import OpenAiCompatibleClient
from app.core.config import settings
from app.core.exceptions import TextCleaningError
from app.services.text_cleaning import LlmCleaner, RuleCleaner, TextCleaningService

logger = logging.getLogger(__name__)


def build_text_cleaning_service(config: dict[str, Any] | None = None) -> TextCleaningService:
    """Build a ``TextCleaningService`` from configuration and environment variables.

    The LLM cleaner is only created when ``mode`` is ``llm`` or ``hybrid`` and a
    supported LLM client package is installed. The API key is read from the
    ``ZHIPU_API_KEY`` environment variable (or the ``zhipu_api_key`` Pydantic setting).
    If the LLM client cannot be configured, the service degrades to rule-only mode.
    """
    cfg = config if config is not None else (settings.ai_config or {}).get("text_cleaning", {})
    rule_cleaner = RuleCleaner(filler_words=cfg.get("filler_words"))
    llm_cleaner = _build_llm_cleaner(cfg) if _mode_uses_llm(cfg) else None
    return TextCleaningService(
        rule_cleaner=rule_cleaner,
        llm_cleaner=llm_cleaner,
        config=cfg,
    )


def _mode_uses_llm(config: dict[str, Any]) -> bool:
    mode = str(config.get("mode", "rule")).lower().strip()
    return mode in {"llm", "hybrid"}


def _build_llm_cleaner(config: dict[str, Any]) -> LlmCleaner | None:
    api_key = settings.zhipu_api_key if hasattr(settings, "zhipu_api_key") else ""
    api_key = api_key or ""
    model = config.get("llm_model", "glm-4-flash")
    temperature = float(config.get("temperature", 0.1))
    max_tokens = int(config.get("max_tokens", 2048))
    batch_size = int(config.get("batch_size", 10))

    if not api_key:
        logger.warning(
            "LLM text cleaning is enabled but ZHIPU_API_KEY is not configured; "
            "falling back to rule cleaning if fallback_on_error is true"
        )
        return None

    try:
        client = _create_openai_compatible_client(api_key)
    except TextCleaningError as exc:
        logger.warning(
            "LLM text cleaning is enabled but client cannot be configured: %s; "
            "falling back to rule cleaning if fallback_on_error is true",
            exc.message,
        )
        return None

    return LlmCleaner(
        client=client,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        batch_size=batch_size,
    )


def _create_openai_compatible_client(api_key: str) -> OpenAiCompatibleClient:
    """Create an OpenAI-compatible client from installed packages."""
    try:
        import openai  # noqa: F401

        client = openai.OpenAI(api_key=api_key)
        return OpenAiCompatibleClient(client)
    except ImportError:
        pass

    try:
        import zhipuai  # noqa: F401

        client = zhipuai.ZhipuAI(api_key=api_key)
        return OpenAiCompatibleClient(client)
    except ImportError:
        pass

    raise TextCleaningError(
        "LLM_NOT_CONFIGURED",
        "no supported LLM client package installed (openai or zhipuai)",
        500,
    )

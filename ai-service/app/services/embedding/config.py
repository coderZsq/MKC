from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from app.core.config import settings

DEFAULT_PROVIDER: str = "zhipuai"
DEFAULT_MODEL: str = "embedding-3"
DEFAULT_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_BATCH_SIZE: int = 64
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_TIMEOUT: int = 30
DEFAULT_DIMENSIONS: int = 2048
DEFAULT_MAX_TEXT_CHARS: int = 8000

_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def _env_values() -> dict[str, str | None]:
    """Return a mapping of environment variables merged with ``.env`` values.

    Environment variables take precedence over values defined in the ``.env`` file.
    """
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    dotenv = dotenv_values(env_path) if env_path.exists() else {}
    merged: dict[str, str | None] = {**dotenv, **os.environ}
    return merged


@dataclass
class EmbeddingConfig:
    """Runtime configuration for the embedding generation service."""

    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    batch_size: int = DEFAULT_BATCH_SIZE
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout: int = DEFAULT_TIMEOUT
    dimensions: int = DEFAULT_DIMENSIONS
    normalize: bool = True
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")
        if self.max_retries < 0:
            raise ValueError("max_retries 不能为负数")
        if self.dimensions <= 0:
            raise ValueError("dimensions 必须大于 0")
        if self.max_text_chars <= 0:
            raise ValueError("max_text_chars 必须大于 0")
        if not self.model:
            raise ValueError("model 不能为空")


def build_embedding_config(config: dict[str, Any] | None = None) -> EmbeddingConfig:
    """Build an ``EmbeddingConfig`` from ``config/ai.yaml`` and environment variables.

    Environment variables referenced as ``${VAR}`` or ``${VAR:-default}`` inside the
    YAML values are expanded. Integer values may be strings in the YAML and are
    coerced after expansion. The provider-specific API key takes precedence over
    the generic ``api_key`` YAML value so OpenAI/Kimi providers do not require a
    ZhipuAI key to be present.
    """
    cfg = config if config is not None else (settings.ai_config or {}).get("embedding", {})
    provider = _resolve_env_value(cfg.get("provider", DEFAULT_PROVIDER))
    return EmbeddingConfig(
        provider=provider,
        model=_resolve_env_value(cfg.get("model", DEFAULT_MODEL)),
        api_key=_provider_specific_api_key(provider, _resolve_env_value(cfg.get("api_key", ""))),
        base_url=_resolve_env_value(cfg.get("base_url", DEFAULT_BASE_URL)),
        batch_size=int(_resolve_env_value(cfg.get("batch_size", DEFAULT_BATCH_SIZE))),
        max_retries=int(_resolve_env_value(cfg.get("max_retries", DEFAULT_MAX_RETRIES))),
        timeout=int(_resolve_env_value(cfg.get("timeout", DEFAULT_TIMEOUT))),
        dimensions=int(_resolve_env_value(cfg.get("dimensions", DEFAULT_DIMENSIONS))),
        normalize=_parse_bool(cfg.get("normalize", True)),
        max_text_chars=int(_resolve_env_value(cfg.get("max_text_chars", DEFAULT_MAX_TEXT_CHARS))),
    )


def _resolve_env_value(value: Any) -> Any:
    """Expand ``${VAR}`` / ``${VAR:-default}`` placeholders in string values."""
    if not isinstance(value, str):
        return value
    if "$" not in value:
        return value
    return _ENV_PLACEHOLDER.sub(_replace_placeholder, value)


def _replace_placeholder(match: re.Match[str]) -> str:
    var_name = match.group(1)
    default = match.group(2)
    env_value = _env_values().get(var_name)
    if env_value is None:
        if default is not None:
            return default
        return ""
    return env_value


def _provider_specific_api_key(provider: str, resolved_api_key: str) -> str:
    """Return the API key for ``provider``, falling back to a generic key.

    The provider-specific environment variable takes precedence, followed by
    ``EMBEDDING_API_KEY`` and finally the resolved YAML value. This keeps the
    existing ``api_key: ${ZHIPU_API_KEY}`` default while allowing OpenAI or Kimi
    providers to work with their own keys.
    """
    env = _env_values()
    generic = env.get("EMBEDDING_API_KEY") or resolved_api_key
    if provider == "zhipuai":
        return env.get("ZHIPU_API_KEY") or generic
    if provider == "openai":
        return env.get("OPENAI_API_KEY") or env.get("KIMI_API_KEY") or generic
    return generic


def _parse_bool(value: Any) -> bool:
    """Parse a YAML/normalized value as a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)

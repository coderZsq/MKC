from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from app.core.config import settings

DEFAULT_PROVIDER: str = "zhipuai"
DEFAULT_ZHIPUAI_MODEL: str = "glm-4-flash"
DEFAULT_KIMI_MODEL: str = "moonshot-v1-8k"
DEFAULT_OLLAMA_MODEL: str = "deepseek-r1:8b"
DEFAULT_ZHIPUAI_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
DEFAULT_OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 2048
DEFAULT_TIMEOUT: int = 60
DEFAULT_MAX_RETRIES: int = 3

_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*?))?\}")


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
class LLMConfig:
    """Runtime configuration for the unified LLM client."""

    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_ZHIPUAI_MODEL
    api_key: str = ""
    base_url: str = DEFAULT_ZHIPUAI_BASE_URL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    fallback_model: str | None = None
    mock_response: str = "这是来自 mock provider 的固定回答。"
    mock_stream_chunks: list[str] = field(default_factory=lambda: ["mock", " ", "answer"])

    def __post_init__(self) -> None:
        if self.provider == "kimi" and self.base_url == DEFAULT_ZHIPUAI_BASE_URL:
            self.base_url = DEFAULT_KIMI_BASE_URL
        if self.provider == "kimi" and self.model == DEFAULT_ZHIPUAI_MODEL:
            self.model = DEFAULT_KIMI_MODEL
        if self.provider == "ollama" and self.base_url == DEFAULT_ZHIPUAI_BASE_URL:
            self.base_url = DEFAULT_OLLAMA_BASE_URL
        if self.provider == "ollama" and self.model == DEFAULT_ZHIPUAI_MODEL:
            self.model = DEFAULT_OLLAMA_MODEL
        if self.max_tokens <= 0:
            raise ValueError("max_tokens 必须大于 0")
        if self.timeout <= 0:
            raise ValueError("timeout 必须大于 0")
        if self.max_retries < 0:
            raise ValueError("max_retries 不能为负数")
        if not self.model:
            raise ValueError("model 不能为空")


def build_llm_config(config: dict[str, Any] | None = None) -> LLMConfig:
    """Build an ``LLMConfig`` from ``config/ai.yaml`` and environment variables.

    Environment variables referenced as ``${VAR}`` or ``${VAR:-default}`` inside
    the YAML values are expanded. Provider-specific API keys take precedence so
    Kimi can use ``KIMI_API_KEY`` while ZhipuAI uses ``ZHIPU_API_KEY``.
    """
    cfg = config if config is not None else (settings.ai_config or {}).get("llm", {})
    provider = _resolve_env_value(cfg.get("provider", DEFAULT_PROVIDER))
    base_url = _resolve_env_value(cfg.get("base_url", DEFAULT_ZHIPUAI_BASE_URL))
    model = _resolve_env_value(cfg.get("model", DEFAULT_ZHIPUAI_MODEL))

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=_provider_specific_api_key(provider, _resolve_env_value(cfg.get("api_key", ""))),
        base_url=base_url,
        temperature=float(_resolve_env_value(cfg.get("temperature", DEFAULT_TEMPERATURE))),
        max_tokens=int(_resolve_env_value(cfg.get("max_tokens", DEFAULT_MAX_TOKENS))),
        timeout=int(_resolve_env_value(cfg.get("timeout", DEFAULT_TIMEOUT))),
        max_retries=int(_resolve_env_value(cfg.get("max_retries", DEFAULT_MAX_RETRIES))),
        fallback_model=_resolve_env_value(cfg.get("fallback_model")),
        mock_response=_resolve_env_value(
            cfg.get("mock_response", "这是来自 mock provider 的固定回答。")
        ),
        mock_stream_chunks=_resolve_env_list(cfg.get("mock_stream_chunks"))
        or ["mock", " ", "answer"],
    )


def _provider_specific_api_key(provider: str, resolved_api_key: str) -> str:
    """Return the API key for ``provider``, falling back to a generic key."""
    env = _env_values()
    generic = env.get("LLM_API_KEY") or resolved_api_key
    if provider == "zhipuai":
        return env.get("ZHIPU_API_KEY") or generic
    if provider == "kimi":
        return env.get("KIMI_API_KEY") or env.get("OPENAI_API_KEY") or generic
    return generic


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


def _resolve_env_list(value: Any) -> list[str] | None:
    """Normalize a YAML list or comma-separated string into a list of strings."""
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return None

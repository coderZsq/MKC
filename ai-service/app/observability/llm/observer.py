from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dotenv import dotenv_values

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "none"
DEFAULT_PROMPT_VERSION = "default"
DEFAULT_MAX_PROMPT_CHARS = 2000
DEFAULT_MAX_COMPLETION_CHARS = 2000
SENSITIVE_PATTERN = re.compile(
    r"(?i)(api[_-]?key|authorization|bearer|jwt|password|secret|token)\s*[:=]\s*([^\s,;]+)"
)


@dataclass(frozen=True)
class LLMObserverConfig:
    provider: str = DEFAULT_PROVIDER
    prompt_version: str = DEFAULT_PROMPT_VERSION
    redact: bool = True
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS
    max_completion_chars: int = DEFAULT_MAX_COMPLETION_CHARS


@dataclass(frozen=True)
class LLMGenerationEvent:
    trace_id: str
    prompt_version: str
    provider: str
    model: str
    prompt: str
    completion: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    status: str
    error_code: str | None = None


class LLMObserver(Protocol):
    def record_generation(self, event: LLMGenerationEvent) -> None: ...  # noqa: D102

    def record_error(self, event: LLMGenerationEvent) -> None: ...  # noqa: D102

    def flush(self) -> None: ...  # noqa: D102


class Redactor:
    def __init__(
        self,
        *,
        enabled: bool = True,
        max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
        max_completion_chars: int = DEFAULT_MAX_COMPLETION_CHARS,
    ) -> None:
        self._enabled = enabled
        self._max_prompt_chars = max_prompt_chars
        self._max_completion_chars = max_completion_chars

    def prompt(self, value: str) -> str:
        return self._sanitize(value, self._max_prompt_chars)

    def completion(self, value: str) -> str:
        return self._sanitize(value, self._max_completion_chars)

    def _sanitize(self, value: str, max_chars: int) -> str:
        text = value
        if not self._enabled:
            return text[:max_chars]
        return SENSITIVE_PATTERN.sub(r"\1=[REDACTED]", text)[:max_chars]


class NoopObserver:
    def record_generation(self, event: LLMGenerationEvent) -> None:
        return None

    def record_error(self, event: LLMGenerationEvent) -> None:
        return None

    def flush(self) -> None:
        return None


def build_llm_observer(config: dict[str, Any] | None = None) -> LLMObserver:
    cfg = build_llm_observer_config(config)
    if cfg.provider in {"", "none", "noop"}:
        return NoopObserver()

    if cfg.provider == "langfuse":
        return _build_langfuse_observer(cfg)
    if cfg.provider == "langsmith":
        return _build_langsmith_observer(cfg)

    logger.warning("Unsupported LLM observability provider %s; using noop", cfg.provider)
    return NoopObserver()


def build_llm_observer_config(config: dict[str, Any] | None = None) -> LLMObserverConfig:
    cfg = config if config is not None else (settings.ai_config or {}).get("llm_observability", {})
    provider = _resolve_env_value(cfg.get("provider", DEFAULT_PROVIDER)).lower()
    return LLMObserverConfig(
        provider=provider,
        prompt_version=str(_resolve_env_value(cfg.get("prompt_version", DEFAULT_PROMPT_VERSION))),
        redact=_parse_bool(_resolve_env_value(cfg.get("redact", True))),
        max_prompt_chars=int(
            _resolve_env_value(cfg.get("max_prompt_chars", DEFAULT_MAX_PROMPT_CHARS))
        ),
        max_completion_chars=int(
            _resolve_env_value(cfg.get("max_completion_chars", DEFAULT_MAX_COMPLETION_CHARS))
        ),
    )


def safe_record_generation(observer: LLMObserver, event: LLMGenerationEvent) -> None:
    try:
        observer.record_generation(event)
    except Exception as exc:
        logger.warning("LLM observer export failed: %s", exc.__class__.__name__)


def safe_record_error(observer: LLMObserver, event: LLMGenerationEvent) -> None:
    try:
        observer.record_error(event)
    except Exception as exc:
        logger.warning("LLM observer export failed: %s", exc.__class__.__name__)


def sanitize_event(event: LLMGenerationEvent, config: LLMObserverConfig) -> LLMGenerationEvent:
    redactor = Redactor(
        enabled=config.redact,
        max_prompt_chars=config.max_prompt_chars,
        max_completion_chars=config.max_completion_chars,
    )
    return LLMGenerationEvent(
        trace_id=event.trace_id,
        prompt_version=event.prompt_version,
        provider=event.provider,
        model=event.model,
        prompt=redactor.prompt(event.prompt),
        completion=redactor.completion(event.completion),
        latency_ms=event.latency_ms,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        total_tokens=event.total_tokens,
        status=event.status,
        error_code=event.error_code,
    )


def _build_langfuse_observer(config: LLMObserverConfig) -> LLMObserver:
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        logger.warning("LLM_OBSERVER_CONFIG_MISSING: Langfuse keys missing; using noop")
        return NoopObserver()
    try:
        from app.observability.llm.langfuse_observer import LangfuseObserver

        return LangfuseObserver(config)
    except Exception as exc:
        logger.warning("LLM_OBSERVER_CONFIG_MISSING: Langfuse unavailable: %s", exc)
        return NoopObserver()


def _build_langsmith_observer(config: LLMObserverConfig) -> LLMObserver:
    if not os.getenv("LANGCHAIN_API_KEY"):
        logger.warning("LLM_OBSERVER_CONFIG_MISSING: LangSmith key missing; using noop")
        return NoopObserver()
    try:
        from app.observability.llm.langsmith_observer import LangSmithObserver

        return LangSmithObserver(config)
    except Exception as exc:
        logger.warning("LLM_OBSERVER_CONFIG_MISSING: LangSmith unavailable: %s", exc)
        return NoopObserver()


def _env_values() -> dict[str, str | None]:
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    dotenv = dotenv_values(env_path) if env_path.exists() else {}
    return {**dotenv, **os.environ}


_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def _resolve_env_value(value: Any) -> Any:
    if not isinstance(value, str) or "$" not in value:
        return value
    env = _env_values()

    def _replace(match: re.Match[str]) -> str:
        env_value = env.get(match.group(1))
        if env_value is None:
            return match.group(2) or ""
        return env_value

    return _ENV_PLACEHOLDER.sub(_replace, value)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() not in {"0", "false", "no", "off"}

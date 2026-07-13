from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class MemoryConfig:
    """Runtime configuration for the long-term memory service."""

    enabled: bool = True
    top_k: int = 5
    score_threshold: float = 0.7
    max_context_tokens: int = 1024
    conversation_prefix: str = "memory:conversation"
    user_prefix: str = "memory:user"

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> MemoryConfig:
        raw = raw or {}
        return cls(
            enabled=_parse_bool(raw.get("enabled", True)),
            top_k=int(raw.get("top_k", 5)),
            score_threshold=float(raw.get("score_threshold", 0.7)),
            max_context_tokens=int(raw.get("max_context_tokens", 1024)),
            conversation_prefix=str(raw.get("conversation_prefix", "memory:conversation")),
            user_prefix=str(raw.get("user_prefix", "memory:user")),
        )


def build_memory_config(config: dict[str, Any] | None = None) -> MemoryConfig:
    """Build a ``MemoryConfig`` from ``config/ai.yaml``.

    Falls back to sensible defaults when the ``memory`` block is missing.
    """
    if config is not None:
        return MemoryConfig.from_dict(config)
    return MemoryConfig.from_dict((settings.ai_config or {}).get("memory", {}))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)

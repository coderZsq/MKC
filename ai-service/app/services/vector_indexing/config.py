from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class VectorIndexingConfig:
    """Runtime configuration for the automatic vector ingestion pipeline."""

    enabled: bool = True
    strategy: str | None = None


def build_vector_indexing_config(
    config: dict[str, Any] | None = None,
) -> VectorIndexingConfig:
    """Build a ``VectorIndexingConfig`` from ``config/ai.yaml`` and environment."""
    cfg = config if config is not None else (settings.ai_config or {}).get("vector_indexing", {})
    return VectorIndexingConfig(
        enabled=_parse_bool(cfg.get("enabled", True)),
        strategy=cfg.get("strategy") or None,
    )


def _parse_bool(value: Any) -> bool:
    """Parse a YAML/normalized value as a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)

from __future__ import annotations

import os
from typing import Any

from app.core.config import settings
from app.services.chunking.chunking_service import ChunkingService
from app.services.chunking.config import DEFAULT_SEPARATORS, ChunkingConfig
from app.services.chunking.token_estimator import TokenEstimator

DEFAULT_CHUNK_SIZE: int = 512
DEFAULT_CHUNK_OVERLAP: int = 50


def build_chunking_config(config: dict[str, Any] | None = None) -> ChunkingConfig:
    """Build a ``ChunkingConfig`` from ``config/ai.yaml`` and environment.

    Environment variables ``CHUNKING_DEFAULT_STRATEGY`` and
    ``CHUNKING_CHUNK_SIZE`` take precedence over the YAML values.
    """
    cfg = config if config is not None else (settings.ai_config or {}).get("chunking", {})
    return ChunkingConfig(
        default_strategy=_env_or_cfg(
            "CHUNKING_DEFAULT_STRATEGY",
            cfg.get("strategy", "paragraph"),
        ),
        chunk_size=int(
            _env_or_cfg(
                "CHUNKING_CHUNK_SIZE",
                cfg.get("chunk_size", DEFAULT_CHUNK_SIZE),
            )
        ),
        chunk_overlap=int(cfg.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)),
        separators=list(cfg.get("separators", DEFAULT_SEPARATORS)),
        preserve_metadata=bool(cfg.get("preserve_metadata", True)),
        max_input_chars=int(
            _env_or_cfg(
                "CHUNKING_MAX_INPUT_CHARS",
                cfg.get("max_input_chars", 1_000_000),
            )
        ),
    )


def build_chunking_service(
    config: ChunkingConfig | None = None,
    estimator: TokenEstimator | None = None,
) -> ChunkingService:
    """Build a ``ChunkingService`` from configuration."""
    cfg = config if config is not None else build_chunking_config()
    return ChunkingService(config=cfg, estimator=estimator)


def _env_or_cfg(env_var: str, default: Any) -> str:
    value = os.environ.get(env_var)
    return str(value) if value is not None else str(default)

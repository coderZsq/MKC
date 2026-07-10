from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.prompt_builder import PromptBuilder
from app.services.retrieval.retrieval_service import (
    RetrievalConfig,
    RetrievalService,
)
from app.vector_store.vector_store import VectorStore

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = RetrievalConfig()


def build_retrieval_config(config: dict[str, Any] | None = None) -> RetrievalConfig:
    """Build a ``RetrievalConfig`` from ``config/ai.yaml`` and defaults."""
    cfg = config if config is not None else (settings.ai_config or {}).get("retrieval", {})
    return RetrievalConfig(
        default_top_k=int(cfg.get("default_top_k", _DEFAULT_CONFIG.default_top_k)),
        score_threshold=float(
            cfg.get("score_threshold", _DEFAULT_CONFIG.score_threshold),
        ),
        max_context_tokens=int(
            cfg.get("max_context_tokens", _DEFAULT_CONFIG.max_context_tokens),
        ),
        prompt_template=str(
            cfg.get("prompt_template", _DEFAULT_CONFIG.prompt_template),
        ),
    )


def build_retrieval_service(
    embedding_svc: EmbeddingService,
    vector_store: VectorStore,
    config: RetrievalConfig | None = None,
) -> RetrievalService:
    """Build a fully configured ``RetrievalService``."""
    cfg = config if config is not None else build_retrieval_config()
    template_path = cfg.prompt_template
    if not Path(template_path).is_absolute():
        project_root = Path(__file__).resolve().parents[3]
        template_path = str(project_root / template_path)
    return RetrievalService(
        embedding_svc=embedding_svc,
        vector_store=vector_store,
        prompt_builder=PromptBuilder(template_path=template_path),
        config=cfg,
    )


__all__ = [
    "RetrievalConfig",
    "RetrievalService",
    "PromptBuilder",
    "build_retrieval_config",
    "build_retrieval_service",
]

from __future__ import annotations

import logging

from app.core.exceptions import VectorStoreConfigError
from app.vector_store.chroma_store import ChromaStore
from app.vector_store.config import VectorStoreConfig, build_vector_store_config
from app.vector_store.milvus_store import MilvusStore
from app.vector_store.vector_store import VectorStore

logger = logging.getLogger(__name__)


SUPPORTED_PROVIDERS: frozenset[str] = frozenset({"milvus", "chroma"})


def build_vector_store(
    config: VectorStoreConfig | None = None,
    allow_fallback: bool = True,
) -> VectorStore:
    """Build a vector store instance from configuration.

    When ``allow_fallback`` is true and the configured primary provider cannot be
    initialised, the factory automatically switches to the fallback provider so
    the service can still start.
    """
    cfg = config if config is not None else build_vector_store_config()
    if cfg.provider not in SUPPORTED_PROVIDERS:
        raise VectorStoreConfigError(f"不支持的 vector store provider: {cfg.provider}")

    try:
        return _build_primary(cfg)
    except Exception as exc:
        if not allow_fallback or cfg.provider == cfg.fallback_provider:
            raise
        logger.warning(
            "Primary vector store %s failed (%s), falling back to %s",
            cfg.provider,
            exc,
            cfg.fallback_provider,
        )
        return _build_fallback(cfg)


def _build_primary(config: VectorStoreConfig) -> VectorStore:
    if config.provider == "chroma":
        return ChromaStore(config)
    return MilvusStore(config)


def _build_fallback(config: VectorStoreConfig) -> VectorStore:
    if config.fallback_provider == "chroma":
        return ChromaStore(
            VectorStoreConfig(
                **{
                    **config.__dict__,
                    "provider": "chroma",
                }
            )
        )
    if config.fallback_provider == "milvus":
        return MilvusStore(
            VectorStoreConfig(
                **{
                    **config.__dict__,
                    "provider": "milvus",
                }
            )
        )
    raise VectorStoreConfigError(
        f"不支持的 fallback vector store provider: {config.fallback_provider}"
    )

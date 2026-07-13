from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.services.hybrid_retrieval.bm25_store import BM25Store
from app.services.hybrid_retrieval.hybrid_retrieval_service import (
    BM25StoreProtocol,
    EmbeddingServiceProtocol,
    HybridRetrievalConfig,
    HybridRetrievalService,
    RerankerProtocol,
    VectorStoreProtocol,
)
from app.services.hybrid_retrieval.reranker import Reranker

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = HybridRetrievalConfig()


def build_hybrid_retrieval_config(
    config: dict[str, Any] | None = None,
) -> HybridRetrievalConfig:
    """Build a ``HybridRetrievalConfig`` from ``config/ai.yaml`` and defaults."""
    cfg = config if config is not None else (settings.ai_config or {}).get("hybrid_retrieval", {})
    bm25_cfg = cfg.get("bm25", {}) or {}
    reranker_cfg = cfg.get("reranker", {}) or {}
    return HybridRetrievalConfig(
        bm25_weight=float(cfg.get("bm25_weight", _DEFAULT_CONFIG.bm25_weight)),
        vector_weight=float(cfg.get("vector_weight", _DEFAULT_CONFIG.vector_weight)),
        rrf_k=int(cfg.get("rrf_k", _DEFAULT_CONFIG.rrf_k)),
        rerank_top_n=int(cfg.get("rerank_top_n", _DEFAULT_CONFIG.rerank_top_n)),
        final_top_k=int(cfg.get("final_top_k", _DEFAULT_CONFIG.final_top_k)),
        score_threshold=float(cfg.get("score_threshold", _DEFAULT_CONFIG.score_threshold)),
        timeout_ms=int(cfg.get("timeout_ms", _DEFAULT_CONFIG.timeout_ms)),
        fallback_to_vector=bool(
            cfg.get("fallback_to_vector", _DEFAULT_CONFIG.fallback_to_vector),
        ),
        bm25_tokenizer=str(bm25_cfg.get("tokenizer", _DEFAULT_CONFIG.bm25_tokenizer)),
        bm25_user_dict=str(bm25_cfg.get("user_dict", _DEFAULT_CONFIG.bm25_user_dict)),
        bm25_cache_index=bool(
            bm25_cfg.get("cache_index", _DEFAULT_CONFIG.bm25_cache_index),
        ),
        bm25_max_docs=int(bm25_cfg.get("max_docs", _DEFAULT_CONFIG.bm25_max_docs)),
        bm25_cache_max_entries=int(
            bm25_cfg.get("cache_max_entries", _DEFAULT_CONFIG.bm25_cache_max_entries),
        ),
        reranker_model_name=str(
            reranker_cfg.get("model_name", _DEFAULT_CONFIG.reranker_model_name),
        ),
        reranker_device=str(reranker_cfg.get("device", _DEFAULT_CONFIG.reranker_device)),
        reranker_max_length=int(
            reranker_cfg.get("max_length", _DEFAULT_CONFIG.reranker_max_length),
        ),
        reranker_enabled=bool(
            reranker_cfg.get("enabled", _DEFAULT_CONFIG.reranker_enabled),
        ),
    )


def build_hybrid_retrieval_service(
    embedding_svc: EmbeddingServiceProtocol,
    vector_store: VectorStoreProtocol,
    config: HybridRetrievalConfig | None = None,
    bm25_store_factory: Any | None = None,
    reranker: RerankerProtocol | None = None,
) -> HybridRetrievalService:
    """Build a fully configured ``HybridRetrievalService``.

    ``bm25_store_factory`` and ``reranker`` are injectable for tests; by
    default they are constructed from ``config``. The reranker model is loaded
    lazily, so constructing this service never blocks on a model download.
    """
    cfg = config if config is not None else build_hybrid_retrieval_config()
    factory = bm25_store_factory or (
        lambda: BM25Store(tokenizer=cfg.bm25_tokenizer, user_dict=cfg.bm25_user_dict)
    )
    reranker_instance = reranker or Reranker(
        model_name=cfg.reranker_model_name,
        device=cfg.reranker_device,
        max_length=cfg.reranker_max_length,
        enabled=cfg.reranker_enabled,
    )
    return HybridRetrievalService(
        bm25_store_factory=factory,
        embedding_svc=embedding_svc,
        vector_store=vector_store,
        reranker=reranker_instance,
        config=cfg,
    )


__all__ = [
    "BM25Store",
    "BM25StoreProtocol",
    "EmbeddingServiceProtocol",
    "HybridRetrievalConfig",
    "HybridRetrievalService",
    "Reranker",
    "RerankerProtocol",
    "VectorStoreProtocol",
    "build_hybrid_retrieval_config",
    "build_hybrid_retrieval_service",
]

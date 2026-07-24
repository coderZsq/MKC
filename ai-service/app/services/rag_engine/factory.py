from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from app.core.exceptions import InvalidRetrievalRequestError, RagEngineUnavailableError
from app.services.rag_engine.config import (
    RagEngineConfig,
    build_rag_engine_config,
    require_llamaindex,
)
from app.services.rag_engine.engine import RagEngine
from app.services.rag_engine.legacy_engine import LegacyRagEngine
from app.services.rag_engine.llamaindex_engine import LlamaIndexRagEngine
from app.services.retrieval.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from app.services.embedding.service import EmbeddingService
    from app.services.llamaindex import LlamaIndexRetrievalEngine
    from app.services.retrieval.retrieval_service import RetrievalService
    from app.vector_store.vector_store import VectorStore

_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class LlamaIndexRetrievalConfig:
    """Lightweight config for constructing the LlamaIndex retrieval engine."""

    def __init__(
        self,
        default_top_k: int = 5,
        score_threshold: float = 0.7,
        max_context_tokens: int = 4096,
        per_resource_candidates: bool = True,
    ) -> None:
        if default_top_k <= 0:
            raise InvalidRetrievalRequestError("default_top_k 必须大于 0")
        if not 0.0 <= score_threshold <= 1.0:
            raise InvalidRetrievalRequestError("score_threshold 必须在 0 到 1 之间")
        if max_context_tokens <= 0:
            raise InvalidRetrievalRequestError("max_context_tokens 必须大于 0")
        self.default_top_k = default_top_k
        self.score_threshold = score_threshold
        self.max_context_tokens = max_context_tokens
        self.per_resource_candidates = per_resource_candidates


def build_rag_engine(
    *,
    config: RagEngineConfig | None = None,
    retrieval_service: RetrievalService | None = None,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
    llamaindex_retrieval_engine: LlamaIndexRetrievalEngine | None = None,
) -> RagEngine:
    """Build the configured RAG engine for QAService."""
    cfg = config if config is not None else build_rag_engine_config()
    if cfg.engine == "legacy":
        if retrieval_service is None:
            raise RagEngineUnavailableError("Legacy RAG 引擎不可用")
        return LegacyRagEngine(retrieval_service)

    require_llamaindex()
    if llamaindex_retrieval_engine is not None:
        return LlamaIndexRagEngine(llamaindex_retrieval_engine)
    if embedding_service is None or vector_store is None:
        raise RagEngineUnavailableError("LlamaIndex RAG 引擎不可用")

    from app.services.llamaindex import (
        LlamaIndexRetrievalConfig as EngineRetrievalConfig,
    )
    from app.services.llamaindex import (
        LlamaIndexRetrievalEngine,
        MKCEmbeddingAdapter,
        build_llamaindex_vector_store,
    )

    embedding_adapter = MKCEmbeddingAdapter(embedding_service)
    vector_adapter = build_llamaindex_vector_store(
        embedding_adapter=embedding_adapter,
        vector_store=vector_store,
    )
    return LlamaIndexRagEngine(
        LlamaIndexRetrievalEngine(
            retriever=cast(Any, vector_adapter),
            prompt_builder=_build_prompt_builder(),
            config=cast(EngineRetrievalConfig, build_llamaindex_retrieval_config()),
        )
    )


def build_llamaindex_retrieval_config(
    config: dict[str, Any] | None = None,
) -> LlamaIndexRetrievalConfig:
    """Build S6-5 retrieval config from ``rag.llamaindex`` values."""
    from app.core.config import settings

    cfg = (
        config
        if config is not None
        else (settings.ai_config or {}).get("rag", {}).get("llamaindex", {})
    )
    default = LlamaIndexRetrievalConfig()
    return LlamaIndexRetrievalConfig(
        default_top_k=int(_resolve_env_value(cfg.get("default_top_k", default.default_top_k))),
        score_threshold=float(
            _resolve_env_value(cfg.get("score_threshold", default.score_threshold))
        ),
        max_context_tokens=int(
            _resolve_env_value(cfg.get("max_context_tokens", default.max_context_tokens))
        ),
        per_resource_candidates=_parse_bool(
            _resolve_env_value(cfg.get("per_resource_candidates", default.per_resource_candidates))
        ),
    )


def _build_prompt_builder() -> PromptBuilder:
    from app.services.retrieval import build_retrieval_config

    retrieval_config = build_retrieval_config()
    template_path = retrieval_config.prompt_template
    if not Path(template_path).is_absolute():
        project_root = Path(__file__).resolve().parents[3]
        template_path = str(project_root / template_path)
    return PromptBuilder(template_path=template_path)


def _resolve_env_value(value: Any) -> Any:
    if not isinstance(value, str) or "$" not in value:
        return value
    return _ENV_PLACEHOLDER.sub(_replace_placeholder, value)


def _replace_placeholder(match: re.Match[str]) -> str:
    var_name = match.group(1)
    default = match.group(2)
    env_value = os.environ.get(var_name)
    if env_value is None:
        return default if default is not None else ""
    return env_value


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

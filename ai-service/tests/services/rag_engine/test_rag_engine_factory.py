from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import RagEngineUnavailableError
from app.models.retrieval import RetrievalRequest, RetrievalResult
from app.services.rag_engine import LegacyRagEngine, LlamaIndexRagEngine, RagEngineConfig
from app.services.rag_engine.factory import build_llamaindex_retrieval_config, build_rag_engine
from app.services.retrieval.retrieval_service import RetrievalService


class _FakeLlamaIndexRetrievalEngine:
    def __init__(self, result: RetrievalResult | None = None) -> None:
        self.result = result or RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
        self.requests: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self.requests.append(request)
        return self.result


def test_factory_builds_legacy_engine() -> None:
    retrieval_service = MagicMock(spec=RetrievalService)

    engine = build_rag_engine(
        config=RagEngineConfig(engine="legacy"),
        retrieval_service=retrieval_service,
    )

    assert isinstance(engine, LegacyRagEngine)


def test_legacy_engine_delegates_to_retrieval_service() -> None:
    result = RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.retrieve.return_value = result
    request = RetrievalRequest(question="q", user_id="u", resource_ids=["r"])

    actual = LegacyRagEngine(retrieval_service).retrieve(request)

    assert actual is result
    retrieval_service.retrieve.assert_called_once_with(request)


def test_factory_builds_llamaindex_engine_from_injected_retrieval_engine() -> None:
    retrieval_engine = _FakeLlamaIndexRetrievalEngine()

    with patch("app.services.rag_engine.factory.require_llamaindex") as require:
        engine = build_rag_engine(
            config=RagEngineConfig(engine="llamaindex"),
            llamaindex_retrieval_engine=retrieval_engine,  # type: ignore[arg-type]
        )

    assert isinstance(engine, LlamaIndexRagEngine)
    require.assert_called_once_with()


def test_llamaindex_engine_delegates_to_retrieval_engine() -> None:
    result = RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
    retrieval_engine = _FakeLlamaIndexRetrievalEngine(result)
    request = RetrievalRequest(question="q", user_id="u", resource_ids=["r"])

    actual = LlamaIndexRagEngine(retrieval_engine).retrieve(request)  # type: ignore[arg-type]

    assert actual is result
    assert retrieval_engine.requests == [request]


def test_factory_reports_missing_legacy_dependencies() -> None:
    with pytest.raises(RagEngineUnavailableError) as exc_info:
        build_rag_engine(config=RagEngineConfig(engine="legacy"))

    assert exc_info.value.code == "RAG_ENGINE_UNAVAILABLE"


def test_factory_reports_missing_llamaindex_dependencies() -> None:
    with (
        patch("app.services.rag_engine.factory.require_llamaindex"),
        pytest.raises(RagEngineUnavailableError) as exc_info,
    ):
        build_rag_engine(config=RagEngineConfig(engine="llamaindex"))

    assert exc_info.value.code == "RAG_ENGINE_UNAVAILABLE"


def test_llamaindex_retrieval_config_reads_nested_rag_config() -> None:
    config = build_llamaindex_retrieval_config(
        {
            "default_top_k": "7",
            "score_threshold": "0.55",
            "max_context_tokens": "2048",
            "per_resource_candidates": "false",
        }
    )

    assert config.default_top_k == 7
    assert config.score_threshold == 0.55
    assert config.max_context_tokens == 2048
    assert config.per_resource_candidates is False

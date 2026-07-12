from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    DimensionMismatchError,
    EmbeddingAuthenticationError,
    EmbeddingProviderError,
    EmbeddingUnavailableError,
)
from app.models.embedding import ChunkInput, Embedding
from app.services.embedding.config import EmbeddingConfig, build_embedding_config
from app.services.embedding.factory import build_embedding_provider
from app.services.embedding.mock import MockEmbeddingProvider
from app.services.embedding.ollama import OllamaEmbeddingProvider
from app.services.embedding.service import EmbeddingService

DIMENSIONS = 8


@pytest.fixture
def config() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider="mock",
        model="embedding-3",
        dimensions=DIMENSIONS,
        batch_size=4,
        max_retries=3,
        normalize=False,
        max_text_chars=100,
    )


def _make_chunks(count: int, text: str = "text") -> list[ChunkInput]:
    return [
        ChunkInput(id=f"c-{index}", resource_id=f"res-{index}", text=f"{text}-{index}")
        for index in range(count)
    ]


class TestEmbeddingService:
    def test_batch_generates_embeddings_for_all_chunks(self, config: EmbeddingConfig) -> None:
        service = EmbeddingService(MockEmbeddingProvider(config), config)
        chunks = _make_chunks(10)

        embeddings = service.embed(chunks)

        assert len(embeddings) == 10
        for embedding in embeddings:
            assert isinstance(embedding, Embedding)
            assert embedding.dimensions == DIMENSIONS
            assert len(embedding.vector) == DIMENSIONS

    def test_batch_splits_exceeding_batch_size(
        self, config: EmbeddingConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = MockEmbeddingProvider(config)
        mock_embed = MagicMock(side_effect=provider.embed)
        monkeypatch.setattr(provider, "embed", mock_embed)
        service = EmbeddingService(provider, config)
        chunks = _make_chunks(10)

        service.embed(chunks)

        assert mock_embed.call_count == 3
        assert len(mock_embed.call_args_list[0].args[0]) == 4
        assert len(mock_embed.call_args_list[1].args[0]) == 4
        assert len(mock_embed.call_args_list[2].args[0]) == 2

    def test_output_order_matches_input(self, config: EmbeddingConfig) -> None:
        service = EmbeddingService(MockEmbeddingProvider(config), config)
        chunks = [
            ChunkInput(id=f"c-{index}", resource_id="r", text=f"t-{index}") for index in range(5)
        ]

        embeddings = service.embed(chunks)

        assert [e.chunk_id for e in embeddings] == [c.id for c in chunks]
        assert [e.resource_id for e in embeddings] == [c.resource_id for c in chunks]

    def test_normalization_produces_unit_vectors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = EmbeddingConfig(dimensions=DIMENSIONS, normalize=True, batch_size=4, max_retries=3)
        service = EmbeddingService(MockEmbeddingProvider(cfg), cfg)
        chunks = _make_chunks(1)
        monkeypatch.setattr("time.sleep", lambda _: None)

        embeddings = service.embed(chunks)

        assert len(embeddings) == 1
        vector = embeddings[0].vector
        norm = sum(component * component for component in vector) ** 0.5
        assert pytest.approx(norm, abs=1e-6) == 1.0

    def test_dimension_validation_passes(self, config: EmbeddingConfig) -> None:
        service = EmbeddingService(MockEmbeddingProvider(config), config)
        chunks = _make_chunks(1)

        embeddings = service.embed(chunks)

        assert len(embeddings) == 1
        assert len(embeddings[0].vector) == DIMENSIONS

    def test_dimension_mismatch_raises(self, config: EmbeddingConfig) -> None:
        class WrongDimensionProvider:
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.0] * (DIMENSIONS - 1) for _ in texts]

        service = EmbeddingService(WrongDimensionProvider(), config)
        with pytest.raises(DimensionMismatchError) as exc_info:
            service.embed(_make_chunks(1))
        assert exc_info.value.code == "DIMENSION_MISMATCH"

    def test_empty_input_returns_empty_list(self, config: EmbeddingConfig) -> None:
        service = EmbeddingService(MockEmbeddingProvider(config), config)
        assert service.embed([]) == []

    def test_empty_text_returns_zero_vector(self, config: EmbeddingConfig) -> None:
        service = EmbeddingService(MockEmbeddingProvider(config), config)
        chunks = [ChunkInput(id="c-empty", resource_id="r", text="")]

        embeddings = service.embed(chunks)

        assert len(embeddings) == 1
        assert embeddings[0].vector == [0.0] * DIMENSIONS

    def test_retry_succeeds_on_third_attempt(
        self, config: EmbeddingConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = MockEmbeddingProvider(config)
        original_embed = provider.embed
        calls: list[list[str]] = []

        def fail_then_succeed(texts: list[str]) -> list[list[float]]:
            calls.append(texts)
            if len(calls) < 3:
                raise RuntimeError("provider down")
            return original_embed(texts)

        monkeypatch.setattr(provider, "embed", fail_then_succeed)
        service = EmbeddingService(provider, config)
        monkeypatch.setattr("time.sleep", lambda _: None)

        embeddings = service.embed(_make_chunks(1))

        assert len(calls) == 3
        assert len(embeddings) == 1

    def test_all_retries_failed_raises_unavailable(
        self, config: EmbeddingConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = MockEmbeddingProvider(config)
        monkeypatch.setattr(provider, "embed", MagicMock(side_effect=RuntimeError("provider down")))
        service = EmbeddingService(provider, config)
        monkeypatch.setattr("time.sleep", lambda _: None)

        with pytest.raises(EmbeddingUnavailableError) as exc_info:
            service.embed(_make_chunks(1))

        assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"
        assert provider.embed.call_count == 3  # type: ignore[attr-defined]

    def test_auth_error_is_not_retried(
        self, config: EmbeddingConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = MockEmbeddingProvider(config)
        monkeypatch.setattr(
            provider, "embed", MagicMock(side_effect=EmbeddingAuthenticationError())
        )
        service = EmbeddingService(provider, config)
        monkeypatch.setattr("time.sleep", lambda _: None)

        with pytest.raises(EmbeddingAuthenticationError) as exc_info:
            service.embed(_make_chunks(1))

        assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"
        assert provider.embed.call_count == 1  # type: ignore[attr-defined]

    def test_provider_vector_count_mismatch_raises(self, config: EmbeddingConfig) -> None:
        class MismatchProvider:
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.0] * DIMENSIONS]

        service = EmbeddingService(MismatchProvider(), config)
        chunks = [
            ChunkInput(id="c-1", resource_id="r", text="first"),
            ChunkInput(id="c-2", resource_id="r", text="second"),
        ]

        with pytest.raises(DimensionMismatchError) as exc_info:
            service.embed(chunks)

        assert exc_info.value.code == "DIMENSION_MISMATCH"
        assert "返回 1 个向量" in exc_info.value.message
        assert "期望 2 个" in exc_info.value.message

    def test_long_text_is_truncated_to_max_text_chars(self, config: EmbeddingConfig) -> None:
        long_text = "a" * (config.max_text_chars + 100)
        received: list[str] = []

        class CaptureProvider:
            def embed(self, texts: list[str]) -> list[list[float]]:
                received.extend(texts)
                return [[0.01 * (index + 1)] * DIMENSIONS for index in range(len(texts))]

        service = EmbeddingService(CaptureProvider(), config)
        service.embed([ChunkInput(id="c-1", resource_id="r", text=long_text)])

        assert len(received) == 1
        assert len(received[0]) == config.max_text_chars

    def test_zero_vector_normalization_returns_zero_vector(self, config: EmbeddingConfig) -> None:
        class ZeroProvider:
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.0] * DIMENSIONS for _ in texts]

        cfg = EmbeddingConfig(dimensions=DIMENSIONS, normalize=True, batch_size=4, max_retries=3)
        service = EmbeddingService(ZeroProvider(), cfg)
        embeddings = service.embed([ChunkInput(id="c-1", resource_id="r", text="hello")])

        assert len(embeddings) == 1
        assert embeddings[0].vector == [0.0] * DIMENSIONS


class TestEmbeddingFactory:
    def test_missing_api_key_blocks_startup(self) -> None:
        cfg = EmbeddingConfig(provider="zhipuai", api_key="")
        with pytest.raises(EmbeddingAuthenticationError) as exc_info:
            build_embedding_provider(cfg)
        assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"

    def test_missing_api_key_blocks_openai_startup(self) -> None:
        cfg = EmbeddingConfig(provider="openai", api_key="")
        with pytest.raises(EmbeddingAuthenticationError) as exc_info:
            build_embedding_provider(cfg)
        assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"

    def test_local_providers_do_not_require_api_key(self) -> None:
        for provider in ("mock", "opensource", "ollama"):
            cfg = EmbeddingConfig(provider=provider, api_key="")
            provider_instance = build_embedding_provider(cfg)
            assert provider_instance is not None

    def test_ollama_provider_built_without_api_key(self) -> None:
        cfg = EmbeddingConfig(provider="ollama", api_key="")
        provider_instance = build_embedding_provider(cfg)
        assert isinstance(provider_instance, OllamaEmbeddingProvider)

    def test_unknown_provider_raises(self) -> None:
        cfg = EmbeddingConfig(provider="unknown", api_key="key")
        with pytest.raises(EmbeddingProviderError) as exc_info:
            build_embedding_provider(cfg)
        assert exc_info.value.code == "EMBEDDING_PROVIDER_ERROR"


class TestEmbeddingConfig:
    def test_openai_provider_uses_openai_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        monkeypatch.setenv("ZHIPU_API_KEY", "")
        cfg = build_embedding_config({"provider": "openai"})
        assert cfg.provider == "openai"
        assert cfg.api_key == "openai-key"

    def test_openai_provider_falls_back_to_kimi_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("KIMI_API_KEY", "kimi-key")
        cfg = build_embedding_config({"provider": "openai"})
        assert cfg.api_key == "kimi-key"

    def test_zhipuai_provider_uses_zhipu_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMBEDDING_PROVIDER", "zhipuai")
        monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-key")
        cfg = build_embedding_config({"provider": "zhipuai"})
        assert cfg.provider == "zhipuai"
        assert cfg.api_key == "zhipu-key"

    def test_normalize_boolean_parsing(self) -> None:
        assert build_embedding_config({"normalize": "false"}).normalize is False
        assert build_embedding_config({"normalize": "true"}).normalize is True
        assert build_embedding_config({"normalize": False}).normalize is False
        assert build_embedding_config({"normalize": True}).normalize is True

    def test_ollama_defaults_applied_when_zhipu_defaults_reused(self) -> None:
        cfg = EmbeddingConfig(provider="ollama")
        assert cfg.model == "bge-m3"
        assert cfg.base_url == "http://localhost:11434/v1"
        assert cfg.dimensions == 1024

    def test_ollama_explicit_values_are_preserved(self) -> None:
        cfg = EmbeddingConfig(
            provider="ollama",
            model="nomic-embed-text",
            base_url="http://host:11434/v1",
            dimensions=768,
        )
        assert cfg.model == "nomic-embed-text"
        assert cfg.base_url == "http://host:11434/v1"
        assert cfg.dimensions == 768

    def test_ollama_api_key_is_optional(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        cfg = build_embedding_config({"provider": "ollama"})
        assert cfg.api_key == ""

    def test_ollama_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OLLAMA_API_KEY", "ollama-proxy-key")
        cfg = build_embedding_config({"provider": "ollama"})
        assert cfg.api_key == "ollama-proxy-key"

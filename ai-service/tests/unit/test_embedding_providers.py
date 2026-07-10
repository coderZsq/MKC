from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import zhipuai
from openai import APIError, AuthenticationError

from app.core.exceptions import EmbeddingAuthenticationError, EmbeddingUnavailableError
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.openai import OpenAiEmbeddingProvider
from app.services.embedding.zhipu import ZhipuEmbeddingProvider

DIMENSIONS = 8


def _build_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider="zhipuai",
        model="embedding-3",
        dimensions=DIMENSIONS,
        api_key="dummy",
        batch_size=4,
        max_retries=1,
        normalize=False,
        max_text_chars=100,
    )


class TestZhipuEmbeddingProvider:
    def test_embed_returns_vectors(self) -> None:
        cfg = _build_config()
        fake_vector = [0.1] * DIMENSIONS
        with patch("app.services.embedding.zhipu.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=fake_vector)]
            )
            mock_client_cls.return_value = mock_client
            provider = ZhipuEmbeddingProvider(cfg)
            vectors = provider.embed(["hello"])
        assert vectors == [fake_vector]

    def test_auth_error_maps_to_embedding_authentication_error(self) -> None:
        cfg = _build_config()
        with patch("app.services.embedding.zhipu.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = zhipuai.APIAuthenticationError(
                "auth failed", response=MagicMock()
            )
            mock_client_cls.return_value = mock_client
            provider = ZhipuEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingAuthenticationError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"

    def test_api_error_maps_to_embedding_unavailable_error(self) -> None:
        cfg = _build_config()
        with patch("app.services.embedding.zhipu.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = zhipuai.APIStatusError(
                "api error", response=MagicMock()
            )
            mock_client_cls.return_value = mock_client
            provider = ZhipuEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

    def test_unexpected_error_maps_to_embedding_unavailable_error(self) -> None:
        cfg = _build_config()
        with patch("app.services.embedding.zhipu.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = RuntimeError("boom")
            mock_client_cls.return_value = mock_client
            provider = ZhipuEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"


class TestOpenAiEmbeddingProvider:
    def test_embed_returns_vectors(self) -> None:
        cfg = _build_config()
        cfg.provider = "openai"
        fake_vector = [0.2] * DIMENSIONS
        with patch("app.services.embedding.openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=fake_vector)]
            )
            mock_client_cls.return_value = mock_client
            provider = OpenAiEmbeddingProvider(cfg)
            vectors = provider.embed(["hello"])
        assert vectors == [fake_vector]

    def test_auth_error_maps_to_embedding_authentication_error(self) -> None:
        cfg = _build_config()
        cfg.provider = "openai"
        with patch("app.services.embedding.openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = AuthenticationError(
                "auth failed", response=MagicMock(), body=None
            )
            mock_client_cls.return_value = mock_client
            provider = OpenAiEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingAuthenticationError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"

    def test_api_error_maps_to_embedding_unavailable_error(self) -> None:
        cfg = _build_config()
        cfg.provider = "openai"
        with patch("app.services.embedding.openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = APIError(
                "api error", request=MagicMock(), body=None
            )
            mock_client_cls.return_value = mock_client
            provider = OpenAiEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

    def test_unexpected_error_maps_to_embedding_unavailable_error(self) -> None:
        cfg = _build_config()
        cfg.provider = "openai"
        with patch("app.services.embedding.openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = RuntimeError("boom")
            mock_client_cls.return_value = mock_client
            provider = OpenAiEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import sentence_transformers
import zhipuai
from openai import APIError, AuthenticationError

from app.core.exceptions import EmbeddingAuthenticationError, EmbeddingUnavailableError
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.ollama import OllamaEmbeddingProvider
from app.services.embedding.openai import OpenAiEmbeddingProvider
from app.services.embedding.opensource import OpenSourceEmbeddingProvider
from app.services.embedding.zhipu import ZhipuEmbeddingProvider

DIMENSIONS = 8


def _build_config(provider: str = "zhipuai") -> EmbeddingConfig:
    return EmbeddingConfig(
        provider=provider,
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
        cfg = _build_config("openai")
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
        cfg = _build_config("openai")
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
        cfg = _build_config("openai")
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
        cfg = _build_config("openai")
        with patch("app.services.embedding.openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = RuntimeError("boom")
            mock_client_cls.return_value = mock_client
            provider = OpenAiEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"


class TestOllamaEmbeddingProvider:
    def test_embed_returns_vectors(self) -> None:
        cfg = _build_config("ollama")
        fake_vector = [0.4] * DIMENSIONS
        with patch("app.services.embedding.ollama.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=fake_vector)]
            )
            mock_client_cls.return_value = mock_client
            provider = OllamaEmbeddingProvider(cfg)
            vectors = provider.embed(["hello"])
        assert vectors == [fake_vector]
        mock_client.embeddings.create.assert_called_once_with(
            model=cfg.model,
            input=["hello"],
        )

    def test_no_api_key_uses_placeholder(self) -> None:
        cfg = EmbeddingConfig(
            provider="ollama",
            api_key="",
            dimensions=DIMENSIONS,
            batch_size=4,
            max_retries=1,
            normalize=False,
            max_text_chars=100,
        )
        with patch("app.services.embedding.ollama.OpenAI") as mock_client_cls:
            OllamaEmbeddingProvider(cfg)
            _, kwargs = mock_client_cls.call_args
            assert kwargs["api_key"] == "ollama"

    def test_auth_error_maps_to_embedding_authentication_error(self) -> None:
        cfg = _build_config("ollama")
        with patch("app.services.embedding.ollama.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = AuthenticationError(
                "auth failed", response=MagicMock(), body=None
            )
            mock_client_cls.return_value = mock_client
            provider = OllamaEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingAuthenticationError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"

    def test_api_error_maps_to_embedding_unavailable_error(self) -> None:
        cfg = _build_config("ollama")
        with patch("app.services.embedding.ollama.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = APIError(
                "api error", request=MagicMock(), body=None
            )
            mock_client_cls.return_value = mock_client
            provider = OllamaEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

    def test_unexpected_error_maps_to_embedding_unavailable_error(self) -> None:
        cfg = _build_config("ollama")
        with patch("app.services.embedding.ollama.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = RuntimeError("boom")
            mock_client_cls.return_value = mock_client
            provider = OllamaEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"


class TestOpenSourceEmbeddingProvider:
    def test_embed_returns_vectors(self) -> None:
        cfg = _build_config("opensource")
        fake_vector = [0.3] * DIMENSIONS
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([fake_vector])

        with patch.object(sentence_transformers, "SentenceTransformer") as mock_transformer_cls:
            mock_transformer_cls.return_value = mock_model
            provider = OpenSourceEmbeddingProvider(cfg)
            vectors = provider.embed(["hello"])

        assert vectors == [fake_vector]
        mock_model.encode.assert_called_once()

    def test_model_is_loaded_lazily(self) -> None:
        cfg = _build_config("opensource")
        with patch.object(sentence_transformers, "SentenceTransformer") as mock_transformer_cls:
            provider = OpenSourceEmbeddingProvider(cfg)
            mock_transformer_cls.assert_not_called()
            provider.embed(["hello"])
            mock_transformer_cls.assert_called_once_with(cfg.model)

    def test_missing_dependency_raises_unavailable(self) -> None:
        cfg = _build_config("opensource")
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            provider = OpenSourceEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

    def test_load_failure_raises_unavailable(self) -> None:
        cfg = _build_config("opensource")
        with patch.object(
            sentence_transformers,
            "SentenceTransformer",
            side_effect=RuntimeError("model download failed"),
        ):
            provider = OpenSourceEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

    def test_inference_failure_raises_unavailable(self) -> None:
        cfg = _build_config("opensource")
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("inference failed")

        with patch.object(sentence_transformers, "SentenceTransformer") as mock_transformer_cls:
            mock_transformer_cls.return_value = mock_model
            provider = OpenSourceEmbeddingProvider(cfg)
            with pytest.raises(EmbeddingUnavailableError) as exc_info:
                provider.embed(["hello"])
            assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"

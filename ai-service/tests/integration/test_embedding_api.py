from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import EmbeddingAuthenticationError
from app.services.embedding.config import EmbeddingConfig, build_embedding_config
from app.services.embedding.factory import (
    build_embedding_config as factory_build_embedding_config,
)
from app.services.embedding.factory import (
    validate_embedding_config,
)
from app.services.embedding.openai import OpenAiEmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.embedding.zhipu import ZhipuEmbeddingProvider

INTERNAL_API_KEY = "test-internal-key"


def _post(client, payload, headers=None):
    merged_headers = {"X-Internal-Key": INTERNAL_API_KEY}
    if headers:
        merged_headers.update(headers)
    return client.post("/ai/v1/embed", headers=merged_headers, json=payload)


class TestEmbeddingEndpoint:
    def test_embed_returns_configured_dimensions(self, client) -> None:
        cfg = build_embedding_config()
        response = _post(
            client,
            {"chunks": [{"id": "c-1", "resource_id": "r-1", "text": "hello world"}]},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        embeddings = body["data"]["embeddings"]
        assert len(embeddings) == 1
        assert embeddings[0]["chunk_id"] == "c-1"
        assert embeddings[0]["resource_id"] == "r-1"
        assert embeddings[0]["model"] == cfg.model
        assert embeddings[0]["dimensions"] == cfg.dimensions
        assert len(embeddings[0]["vector"]) == cfg.dimensions

    def test_embed_empty_batch_returns_400(self, client) -> None:
        response = _post(client, {"chunks": []})
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "EMPTY_BATCH"

    def test_embed_invalid_request_returns_validation_error(self, client) -> None:
        response = _post(client, {"chunks": "not-a-list"})
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_embed_unexpected_service_error_returns_500(self, app, client) -> None:
        mock_service = MagicMock()
        mock_service.embed.side_effect = RuntimeError("boom")
        app.extensions["embedding"] = mock_service
        response = _post(
            client,
            {"chunks": [{"id": "c-1", "resource_id": "r-1", "text": "hello"}]},
        )
        assert response.status_code == 500
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "EMBEDDING_INTERNAL_ERROR"

    def test_embed_missing_internal_key_returns_401(self, client) -> None:
        response = client.post(
            "/ai/v1/embed",
            json={"chunks": [{"id": "c-1", "resource_id": "r-1", "text": "hello"}]},
        )
        assert response.status_code == 401
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_embed_zhipuai_provider_returns_vectors(self, app, client, monkeypatch) -> None:
        monkeypatch.setenv("ZHIPU_API_KEY", "dummy")
        fake_vector = [0.01] * 2048

        with patch("app.services.embedding.zhipu.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=fake_vector)]
            )
            mock_client_cls.return_value = mock_client

            cfg = EmbeddingConfig(
                provider="zhipuai",
                model="embedding-3",
                api_key="dummy",
                dimensions=2048,
            )
            app.extensions["embedding"] = EmbeddingService(ZhipuEmbeddingProvider(cfg), cfg)

            response = _post(
                client,
                {"chunks": [{"id": "c-1", "resource_id": "r-1", "text": "hello"}]},
            )

        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert len(body["data"]["embeddings"][0]["vector"]) == 2048

    def test_embed_openai_provider_returns_vectors(self, app, client, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "dummy")
        fake_vector = [0.02] * 2048

        with patch("app.services.embedding.openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=fake_vector)]
            )
            mock_client_cls.return_value = mock_client

            cfg = EmbeddingConfig(
                provider="openai",
                model="text-embedding-3-small",
                api_key="dummy",
                dimensions=2048,
            )
            app.extensions["embedding"] = EmbeddingService(OpenAiEmbeddingProvider(cfg), cfg)

            response = _post(
                client,
                {"chunks": [{"id": "c-1", "resource_id": "r-1", "text": "hello"}]},
            )

        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert len(body["data"]["embeddings"][0]["vector"]) == 2048

    def test_embed_100_chunks_under_five_seconds(self, app, client) -> None:
        cfg = build_embedding_config()
        mock_provider = MagicMock()
        mock_provider.embed.side_effect = lambda texts: [[0.01] * cfg.dimensions for _ in texts]
        app.extensions["embedding"] = EmbeddingService(mock_provider, cfg)

        chunks = [
            {"id": f"c-{index}", "resource_id": "r-1", "text": f"chunk {index}"}
            for index in range(100)
        ]
        start = time.monotonic()
        response = _post(client, {"chunks": chunks})
        elapsed = time.monotonic() - start
        assert response.status_code == 200
        body = response.get_json()
        assert len(body["data"]["embeddings"]) == 100
        assert elapsed < 5.0


class TestEmbeddingStartupValidation:
    def test_validate_config_blocks_startup_when_zhipuai_key_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("EMBEDDING_PROVIDER", "zhipuai")
        monkeypatch.setenv("ZHIPU_API_KEY", "")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        cfg = factory_build_embedding_config()
        with pytest.raises(EmbeddingAuthenticationError) as exc_info:
            validate_embedding_config(cfg)
        assert exc_info.value.code == "EMBEDDING_AUTH_FAILED"

    def test_validate_config_allows_local_providers_without_key(self) -> None:
        for provider in ("mock", "opensource"):
            cfg = factory_build_embedding_config({"provider": provider, "api_key": ""})
            validate_embedding_config(cfg)  # should not raise

    def test_create_app_accepts_injected_embedding_service(self) -> None:
        from app import create_app

        mock_service = MagicMock()
        mock_service.embed.return_value = []
        app = create_app(embedding_service=mock_service)
        assert app.extensions["embedding"] is mock_service

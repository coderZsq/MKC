from __future__ import annotations

from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.mock import MockEmbeddingProvider
from app.services.embedding.service import EmbeddingService


class TestEmbeddingServiceEmbedQuery:
    def test_embed_query_returns_single_vector(self) -> None:
        config = EmbeddingConfig(
            provider="mock",
            model="embedding-3",
            dimensions=8,
            batch_size=4,
            max_retries=3,
            normalize=False,
            max_text_chars=100,
        )
        service = EmbeddingService(MockEmbeddingProvider(config), config)

        vector = service.embed_query("hello")

        assert len(vector) == 8

    def test_embed_query_empty_text_returns_zero_vector(self) -> None:
        config = EmbeddingConfig(
            provider="mock",
            model="embedding-3",
            dimensions=8,
            batch_size=4,
            max_retries=3,
            normalize=False,
            max_text_chars=100,
        )
        service = EmbeddingService(MockEmbeddingProvider(config), config)

        vector = service.embed_query("")

        assert vector == [0.0] * 8

from __future__ import annotations

import asyncio

import pytest

from app.core.exceptions import EmbeddingUnavailableError
from app.services.llamaindex.embedding_adapter import MKCEmbeddingAdapter


class _FakeEmbeddingService:
    def __init__(self, vector: list[float] | None = None, error: Exception | None = None) -> None:
        self.vector = vector or [0.1, 0.2, 0.3]
        self.error = error
        self.calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.vector


def test_embedding_adapter_uses_existing_embed_query() -> None:
    service = _FakeEmbeddingService(vector=[0.4, 0.5])
    adapter = MKCEmbeddingAdapter(service)

    embedding = adapter.get_query_embedding("how to search")

    assert embedding == [0.4, 0.5]
    assert service.calls == ["how to search"]


def test_embedding_adapter_text_embedding_reuses_embed_query() -> None:
    service = _FakeEmbeddingService(vector=[0.7])
    adapter = MKCEmbeddingAdapter(service)

    embedding = adapter.get_text_embedding("document chunk")

    assert embedding == [0.7]
    assert service.calls == ["document chunk"]


def test_embedding_adapter_async_query_falls_back_to_sync_service() -> None:
    service = _FakeEmbeddingService(vector=[0.9])
    adapter = MKCEmbeddingAdapter(service)

    embedding = asyncio.run(adapter.aget_query_embedding("async query"))

    assert embedding == [0.9]
    assert service.calls == ["async query"]


def test_embedding_adapter_maps_unexpected_errors() -> None:
    adapter = MKCEmbeddingAdapter(_FakeEmbeddingService(error=RuntimeError("provider down")))

    with pytest.raises(EmbeddingUnavailableError) as exc_info:
        adapter.get_query_embedding("boom")

    assert exc_info.value.code == "EMBEDDING_UNAVAILABLE"
    assert exc_info.value.status_code == 503


def test_embedding_adapter_preserves_existing_embedding_unavailable_error() -> None:
    adapter = MKCEmbeddingAdapter(
        _FakeEmbeddingService(error=EmbeddingUnavailableError("upstream unavailable"))
    )

    with pytest.raises(EmbeddingUnavailableError) as exc_info:
        adapter.get_query_embedding("boom")

    assert exc_info.value.message == "upstream unavailable"

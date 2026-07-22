from __future__ import annotations

from typing import Any

import pytest

from app.core.exceptions import InvalidRetrievalFilterError, VectorStoreUnavailableError
from app.models.vector_record import VectorSearchResult
from app.services.llamaindex.filters import build_metadata_filters
from app.services.llamaindex.milvus_adapter import (
    MKCVectorStoreAdapter,
    build_llamaindex_vector_store,
)
from app.vector_store.config import VectorStoreConfig


class _FakeEmbeddingAdapter:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [0.1, 0.2]
        self.calls: list[str] = []

    def get_query_embedding(self, query: str) -> list[float]:
        self.calls.append(query)
        return self.vector


class _FakeVectorStore:
    def __init__(
        self,
        results: list[VectorSearchResult] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.search_calls: list[dict[str, Any]] = []

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        self.search_calls.append({"vector": vector, "top_k": top_k, "filters": filters})
        if self.error is not None:
            raise self.error
        return self.results


def _config() -> VectorStoreConfig:
    return VectorStoreConfig(
        provider="milvus",
        collection_name="mkc_chunks",
        uri="http://milvus:19530",
        dimensions=1024,
    )


def test_build_metadata_filters_for_single_resource() -> None:
    filters = build_metadata_filters(user_id=" user-1 ", resource_ids=[" res-1 "])

    assert filters == {"user_id": "user-1", "resource_ids": ["res-1"]}


def test_build_metadata_filters_for_multiple_resources() -> None:
    filters = build_metadata_filters(
        user_id="user-1",
        resource_ids=["res-1", "res-2", "res-1"],
    )

    assert filters == {"user_id": "user-1", "resource_ids": ["res-1", "res-2"]}


def test_build_metadata_filters_rejects_missing_user_id() -> None:
    with pytest.raises(InvalidRetrievalFilterError) as exc_info:
        build_metadata_filters(user_id=" ", resource_ids=["res-1"])

    assert exc_info.value.code == "INVALID_RETRIEVAL_FILTER"
    assert exc_info.value.status_code == 400


def test_build_metadata_filters_rejects_empty_resource_ids() -> None:
    with pytest.raises(InvalidRetrievalFilterError) as exc_info:
        build_metadata_filters(user_id="user-1", resource_ids=[" ", ""])

    assert exc_info.value.code == "INVALID_RETRIEVAL_FILTER"
    assert exc_info.value.status_code == 400


def test_vector_store_adapter_searches_legacy_store_and_returns_nodes() -> None:
    store = _FakeVectorStore(
        results=[
            VectorSearchResult(
                id="chunk-1",
                resource_id="res-1",
                user_id="user-1",
                text="retrieved text",
                metadata={"source_type": "pdf"},
                score=0.88,
            )
        ]
    )
    embedding = _FakeEmbeddingAdapter(vector=[0.3, 0.4])
    adapter = MKCVectorStoreAdapter(store, embedding, _config())

    nodes = adapter.query("question", user_id="user-1", resource_ids=["res-1"], top_k=7)

    assert embedding.calls == ["question"]
    assert store.search_calls == [
        {
            "vector": [0.3, 0.4],
            "top_k": 7,
            "filters": {"user_id": "user-1", "resource_ids": ["res-1"]},
        }
    ]
    assert len(nodes) == 1
    assert nodes[0].node_id == "chunk-1"
    assert nodes[0].get_content() == "retrieved text"
    assert nodes[0].metadata["score"] == 0.88
    assert nodes[0].metadata["user_id"] == "user-1"


def test_vector_store_adapter_clamps_top_k_to_existing_config_limit() -> None:
    store = _FakeVectorStore()
    adapter = MKCVectorStoreAdapter(store, _FakeEmbeddingAdapter(), _config())

    adapter.search_by_vector(
        vector=[0.1],
        filters={"user_id": "user-1", "resource_ids": ["res-1"]},
        top_k=999,
    )

    assert store.search_calls[0]["top_k"] == 100


def test_vector_store_adapter_maps_search_errors() -> None:
    adapter = MKCVectorStoreAdapter(
        _FakeVectorStore(error=RuntimeError("milvus unavailable")),
        _FakeEmbeddingAdapter(),
        _config(),
    )

    with pytest.raises(VectorStoreUnavailableError) as exc_info:
        adapter.search_by_vector(
            vector=[0.1],
            filters={"user_id": "user-1", "resource_ids": ["res-1"]},
            top_k=3,
        )

    assert exc_info.value.code == "VECTOR_STORE_UNAVAILABLE"
    assert exc_info.value.status_code == 503


def test_build_llamaindex_vector_store_uses_existing_config_and_store() -> None:
    config = _config()
    store = _FakeVectorStore()
    embedding = _FakeEmbeddingAdapter()

    adapter = build_llamaindex_vector_store(
        embedding_adapter=embedding,
        config=config,
        vector_store=store,
    )

    assert adapter.collection_name == "mkc_chunks"
    assert adapter.dimensions == 1024
    assert adapter.config is config


def test_build_llamaindex_vector_store_maps_factory_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config()

    def _raise_factory_error(_: VectorStoreConfig) -> _FakeVectorStore:
        raise RuntimeError("connection failed")

    monkeypatch.setattr(
        "app.services.llamaindex.milvus_adapter.build_vector_store",
        _raise_factory_error,
    )

    with pytest.raises(VectorStoreUnavailableError) as exc_info:
        build_llamaindex_vector_store(embedding_adapter=_FakeEmbeddingAdapter(), config=config)

    assert exc_info.value.code == "VECTOR_STORE_UNAVAILABLE"

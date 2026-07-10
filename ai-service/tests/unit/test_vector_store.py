from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import chromadb
import pytest
from pymilvus import MilvusClient

from app.core.exceptions import VectorStoreConfigError, VectorStoreUnavailableError
from app.models.vector_record import VectorRecord
from app.vector_store import ChromaStore, MilvusStore, build_vector_store, build_vector_store_config
from app.vector_store.config import VectorStoreConfig


def _record(
    record_id: str = "r1",
    resource_id: str = "res1",
    user_id: str = "u1",
    text: str = "hello",
    vector: list[float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> VectorRecord:
    return VectorRecord(
        id=record_id,
        resource_id=resource_id,
        user_id=user_id,
        text=text,
        vector=vector or [1.0, 0.0, 0.0],
        metadata=metadata or {"title": "test"},
    )


class TestChromaStore:
    @pytest.fixture
    def store(self) -> ChromaStore:
        config = VectorStoreConfig(dimensions=3, collection_name=f"test_{uuid.uuid4().hex}")
        return ChromaStore(config, client=chromadb.Client())

    def test_upsert_and_search(self, store: ChromaStore) -> None:
        record = _record(vector=[1.0, 0.0, 0.0])
        assert store.upsert([record]) == 1

        results = store.search([1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].id == record.id
        assert results[0].resource_id == record.resource_id
        assert results[0].score == pytest.approx(1.0, abs=0.01)

    def test_upsert_empty_batch_returns_zero(self, store: ChromaStore) -> None:
        assert store.upsert([]) == 0

    def test_delete_by_resource(self, store: ChromaStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1"),
                _record(record_id="b", resource_id="res2"),
            ]
        )
        assert store.delete_by_resource("res1") == 1
        results = store.search([1.0, 0.0, 0.0], top_k=10)
        assert {r.id for r in results} == {"b"}

    def test_delete_by_resource_and_user(self, store: ChromaStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1", user_id="u1"),
                _record(record_id="b", resource_id="res1", user_id="u2"),
            ]
        )
        assert store.delete_by_resource("res1", user_id="u1") == 1
        results = store.search([1.0, 0.0, 0.0], top_k=10)
        assert {r.id for r in results} == {"b"}

    def test_search_with_filters(self, store: ChromaStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1", user_id="u1"),
                _record(record_id="b", resource_id="res2", user_id="u2"),
            ]
        )
        results = store.search([1.0, 0.0, 0.0], filters={"resource_id": "res1"})
        assert len(results) == 1
        assert results[0].id == "a"

    def test_search_with_multiple_resource_ids(self, store: ChromaStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1", user_id="u1"),
                _record(record_id="b", resource_id="res2", user_id="u1"),
                _record(record_id="c", resource_id="res3", user_id="u1"),
            ]
        )
        results = store.search(
            [1.0, 0.0, 0.0],
            filters={"resource_ids": ["res1", "res2"], "user_id": "u1"},
        )
        assert {r.id for r in results} == {"a", "b"}

    def test_search_with_empty_resource_ids_list_returns_empty(self, store: ChromaStore) -> None:
        store.upsert([_record(record_id="a", resource_id="res1", user_id="u1")])
        results = store.search(
            [1.0, 0.0, 0.0],
            filters={"resource_ids": [], "user_id": "u1"},
        )
        assert results == []

    def test_search_returns_metadata_without_reserved_keys(self, store: ChromaStore) -> None:
        record = _record(metadata={"custom": "value"})
        store.upsert([record])
        results = store.search([1.0, 0.0, 0.0], top_k=1)
        assert results[0].metadata == {"custom": "value"}

    def test_delete_nonexistent_resource_returns_zero(self, store: ChromaStore) -> None:
        assert store.delete_by_resource("missing") == 0

    def test_upsert_error_is_wrapped(self, store: ChromaStore) -> None:
        store._collection = MagicMock()
        store._collection.upsert.side_effect = RuntimeError("boom")
        with pytest.raises(VectorStoreUnavailableError):
            store.upsert([_record()])

    def test_search_error_is_wrapped(self, store: ChromaStore) -> None:
        store._collection = MagicMock()
        store._collection.query.side_effect = RuntimeError("boom")
        with pytest.raises(VectorStoreUnavailableError):
            store.search([1.0, 0.0, 0.0])


class TestMilvusStore:
    @pytest.fixture
    def store(self, tmp_path: pytest.TempPathFactory) -> MilvusStore:
        db_path = tmp_path / "milvus.db"  # type: ignore[operator]
        config = VectorStoreConfig(
            provider="milvus",
            uri=str(db_path),
            dimensions=8,
            collection_name=f"test_{uuid.uuid4().hex}",
            max_retries=1,
        )
        client = MilvusClient(uri=config.uri)
        return MilvusStore(config, client=client)

    def test_upsert_and_search(self, store: MilvusStore) -> None:
        record = _record(vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert store.upsert([record]) == 1

        results = store.search([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].id == record.id
        assert results[0].resource_id == record.resource_id

    def test_upsert_empty_batch_returns_zero(self, store: MilvusStore) -> None:
        assert store.upsert([]) == 0

    def test_delete_by_resource(self, store: MilvusStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1", vector=[1.0] * 8),
                _record(record_id="b", resource_id="res2", vector=[0.0, 1.0] + [0.0] * 6),
            ]
        )
        assert store.delete_by_resource("res1") == 1
        results = store.search([0.0, 1.0] + [0.0] * 6, top_k=10)
        assert {r.id for r in results} == {"b"}

    def test_search_with_filters(self, store: MilvusStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1", user_id="u1", vector=[1.0] * 8),
                _record(
                    record_id="b", resource_id="res2", user_id="u2", vector=[0.0, 1.0] + [0.0] * 6
                ),
            ]
        )
        results = store.search([1.0] * 8, filters={"resource_id": "res1", "user_id": "u1"})
        assert len(results) == 1
        assert results[0].id == "a"

    def test_search_with_multiple_resource_ids(self, store: MilvusStore) -> None:
        store.upsert(
            [
                _record(record_id="a", resource_id="res1", user_id="u1", vector=[1.0] * 8),
                _record(record_id="b", resource_id="res2", user_id="u1", vector=[1.0] * 8),
                _record(record_id="c", resource_id="res3", user_id="u1", vector=[1.0] * 8),
            ]
        )
        results = store.search(
            [1.0] * 8,
            filters={"resource_ids": ["res1", "res2"], "user_id": "u1"},
        )
        assert {r.id for r in results} == {"a", "b"}

    def test_dimension_mismatch_raises_config_error(self, tmp_path: Any) -> None:
        db_path = tmp_path / "milvus_dim.db"
        collection_name = f"dim_{uuid.uuid4().hex}"
        config_a = VectorStoreConfig(
            provider="milvus", uri=str(db_path), dimensions=8, collection_name=collection_name
        )
        MilvusStore(config_a)

        config_b = VectorStoreConfig(
            provider="milvus", uri=str(db_path), dimensions=16, collection_name=collection_name
        )
        with pytest.raises(VectorStoreConfigError):
            MilvusStore(config_b)

    def test_milvus_unavailable_error_is_wrapped(self) -> None:
        config = VectorStoreConfig(provider="milvus", uri="/dev/null/invalid.db")
        with pytest.raises(VectorStoreUnavailableError):
            MilvusStore(config)


class TestBuildVectorStore:
    def test_build_vector_store_returns_chroma(self) -> None:
        config = VectorStoreConfig(provider="chroma")
        store = build_vector_store(config)
        assert isinstance(store, ChromaStore)

    def test_build_vector_store_falls_back_to_chroma(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VECTOR_STORE_PROVIDER", "milvus")
        monkeypatch.setenv("VECTOR_STORE_URI", "/dev/null/invalid.db")
        config = build_vector_store_config()
        store = build_vector_store(config)
        assert isinstance(store, ChromaStore)

    def test_build_vector_store_no_fallback_raises(self) -> None:
        config = VectorStoreConfig(provider="milvus", uri="/dev/null/invalid.db")
        with pytest.raises(VectorStoreUnavailableError):
            build_vector_store(config, allow_fallback=False)

    def test_unsupported_provider_raises(self) -> None:
        config = VectorStoreConfig(provider="unknown")
        with pytest.raises(VectorStoreConfigError):
            build_vector_store(config)


class TestConfig:
    def test_invalid_dimensions_raises(self) -> None:
        with pytest.raises(ValueError):
            VectorStoreConfig(dimensions=0)

    def test_negative_retries_raise(self) -> None:
        with pytest.raises(ValueError):
            VectorStoreConfig(max_retries=-1)

    def test_env_resolution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VECTOR_STORE_PROVIDER", "chroma")
        monkeypatch.setenv("VECTOR_STORE_DIMENSIONS", "128")
        config = build_vector_store_config()
        assert config.provider == "chroma"
        assert config.dimensions == 128

    def test_env_default_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VECTOR_STORE_PROVIDER", raising=False)
        config = build_vector_store_config()
        assert config.provider == "milvus"

from __future__ import annotations

from typing import Any, Protocol

from llama_index.core.schema import TextNode

from app.core.exceptions import VectorStoreUnavailableError
from app.services.llamaindex.filters import build_metadata_filters
from app.services.llamaindex.metadata_mapper import vector_search_result_to_node
from app.vector_store.config import VectorStoreConfig, build_vector_store_config
from app.vector_store.factory import build_vector_store
from app.vector_store.vector_store import VectorStore


class EmbeddingAdapterProtocol(Protocol):
    def get_query_embedding(self, query: str) -> list[float]: ...


class MKCVectorStoreAdapter:
    """LlamaIndex-facing retriever wrapper around the legacy MKC VectorStore."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_adapter: EmbeddingAdapterProtocol,
        config: VectorStoreConfig,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_adapter = embedding_adapter
        self.config = config
        self.collection_name = config.collection_name
        self.dimensions = config.dimensions

    def query(
        self,
        query: str,
        *,
        user_id: str,
        resource_ids: list[str],
        top_k: int = 10,
    ) -> list[TextNode]:
        filters = build_metadata_filters(user_id=user_id, resource_ids=resource_ids)
        vector = self._embedding_adapter.get_query_embedding(query)
        return self.search_by_vector(vector=vector, filters=filters, top_k=top_k)

    def search_by_vector(
        self,
        *,
        vector: list[float],
        filters: dict[str, Any],
        top_k: int = 10,
    ) -> list[TextNode]:
        try:
            results = self._vector_store.search(
                vector,
                top_k=min(top_k, self.config.top_k_limit),
                filters=filters,
            )
        except VectorStoreUnavailableError:
            raise
        except Exception as exc:
            raise VectorStoreUnavailableError("向量存储不可用") from exc
        return [vector_search_result_to_node(result) for result in results]


def build_llamaindex_vector_store(
    embedding_adapter: EmbeddingAdapterProtocol,
    config: VectorStoreConfig | None = None,
    vector_store: VectorStore | None = None,
) -> MKCVectorStoreAdapter:
    """Build a LlamaIndex-compatible wrapper from existing vector-store config."""
    try:
        cfg = config if config is not None else build_vector_store_config()
        store = vector_store if vector_store is not None else build_vector_store(cfg)
    except VectorStoreUnavailableError:
        raise
    except Exception as exc:
        raise VectorStoreUnavailableError("向量存储不可用") from exc
    return MKCVectorStoreAdapter(
        vector_store=store, embedding_adapter=embedding_adapter, config=cfg
    )

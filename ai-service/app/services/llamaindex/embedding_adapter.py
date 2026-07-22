from __future__ import annotations

from typing import Protocol

from llama_index.core.base.embeddings.base import BaseEmbedding, Embedding
from llama_index.core.bridge.pydantic import PrivateAttr

from app.core.exceptions import EmbeddingUnavailableError


class EmbeddingServiceProtocol(Protocol):
    def embed_query(self, text: str) -> list[float]: ...


class MKCEmbeddingAdapter(BaseEmbedding):
    """LlamaIndex embedding adapter backed by MKC's existing embedding service."""

    _embedding_service: EmbeddingServiceProtocol = PrivateAttr()

    def __init__(
        self,
        embedding_service: EmbeddingServiceProtocol,
        model_name: str = "mkc-embedding",
    ) -> None:
        super().__init__(model_name=model_name)
        self._embedding_service = embedding_service

    @classmethod
    def class_name(cls) -> str:
        return "MKCEmbeddingAdapter"

    def _get_query_embedding(self, query: str) -> Embedding:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> Embedding:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> Embedding:
        return self._embed(text)

    def _embed(self, text: str) -> Embedding:
        try:
            return self._embedding_service.embed_query(text)
        except EmbeddingUnavailableError:
            raise
        except Exception as exc:
            raise EmbeddingUnavailableError("向量生成不可用") from exc

from __future__ import annotations

import asyncio
import logging
import uuid

from app.models.embedding import ChunkInput
from app.models.vector_record import VectorRecord
from app.services.embedding.service import EmbeddingService
from app.services.memory.config import MemoryConfig, build_memory_config
from app.vector_store.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemoryService:
    """Long-term memory for conversations and user facts.

    Memories are stored as vector records keyed by synthetic ``resource_id``
    values so they live alongside document chunks without colliding with real
    resources.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        config: MemoryConfig,
    ) -> None:
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._config = config

    async def load_context(self, user_id: str, conversation_id: str, question: str) -> str:
        """Retrieve relevant long-term memory snippets for ``question``."""
        if not self._config.enabled:
            return ""

        try:
            vector = await asyncio.to_thread(self._embedding.embed_query, question)
            resource_ids = [
                f"{self._config.conversation_prefix}:{conversation_id}",
                f"{self._config.user_prefix}:{user_id}",
            ]
            results = await asyncio.to_thread(
                self._vector_store.search,
                vector,
                self._config.top_k,
                {"user_id": user_id, "resource_ids": resource_ids},
            )
        except Exception:
            logger.exception("Failed to load long-term memory")
            return ""

        filtered = [r for r in results if r.score >= self._config.score_threshold]
        filtered.sort(key=lambda r: r.score, reverse=True)

        snippets: list[str] = []
        total_tokens = 0
        for result in filtered:
            text = result.text.strip()
            if not text:
                continue
            tokens = _estimate_tokens(text)
            if total_tokens + tokens > self._config.max_context_tokens:
                break
            snippets.append(text)
            total_tokens += tokens

        if not snippets:
            return ""

        return (
            "=== 长期记忆（可能与当前问题相关）===\n"
            + "\n".join(f"- {snippet}" for snippet in snippets)
            + "\n===================================="
        )

    async def save_turn(
        self,
        user_id: str,
        conversation_id: str,
        question: str,
        answer: str,
        reasoning: str = "",
    ) -> None:
        """Persist a single Q&A turn as a conversation memory vector."""
        if not self._config.enabled:
            return

        if not question.strip() or not answer.strip():
            return

        text = f"User: {question}\nAssistant: {answer}"
        if reasoning and reasoning.strip():
            text += f"\nReasoning: {reasoning.strip()}"

        try:
            embeddings = await asyncio.to_thread(
                self._embedding.embed,
                [
                    ChunkInput(
                        id=str(uuid.uuid4()),
                        resource_id=f"{self._config.conversation_prefix}:{conversation_id}",
                        text=text,
                    )
                ],
            )
            if not embeddings:
                return
            record = VectorRecord(
                id=str(uuid.uuid4()),
                resource_id=f"{self._config.conversation_prefix}:{conversation_id}",
                user_id=user_id,
                text=text,
                vector=embeddings[0].vector,
                metadata={"memory_type": "turn"},
            )
            await asyncio.to_thread(self._vector_store.upsert, [record])
        except Exception:
            logger.exception("Failed to save conversation turn to long-term memory")

    async def save_user_facts(self, user_id: str, facts: list[str]) -> None:
        """Persist explicit user facts to long-term user memory."""
        if not self._config.enabled or not facts:
            return

        chunks = [
            ChunkInput(
                id=str(uuid.uuid4()),
                resource_id=f"{self._config.user_prefix}:{user_id}",
                text=fact.strip(),
            )
            for fact in facts
            if fact.strip()
        ]
        if not chunks:
            return

        try:
            embeddings = await asyncio.to_thread(self._embedding.embed, chunks)
            records = [
                VectorRecord(
                    id=chunk.id,
                    resource_id=chunk.resource_id,
                    user_id=user_id,
                    text=chunk.text,
                    vector=embedding.vector,
                    metadata={"memory_type": "user_fact"},
                )
                for chunk, embedding in zip(chunks, embeddings, strict=False)
            ]
            await asyncio.to_thread(self._vector_store.upsert, records)
        except Exception:
            logger.exception("Failed to save user facts to long-term memory")


def _estimate_tokens(text: str) -> int:
    """Rough token estimate matching the gateway heuristic."""
    return (len(text) + 1) // 2


def build_memory_service(
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    config: MemoryConfig | None = None,
) -> MemoryService:
    """Build a fully configured ``MemoryService``."""
    cfg = config if config is not None else build_memory_config()
    return MemoryService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        config=cfg,
    )

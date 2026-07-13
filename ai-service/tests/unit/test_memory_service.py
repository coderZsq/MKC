from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from app.models.vector_record import VectorRecord, VectorSearchResult
from app.services.memory import MemoryConfig, MemoryService


def _run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_service(
    *, top_k: int = 5, score_threshold: float = 0.7, max_context_tokens: int = 1024
) -> tuple[MemoryService, MagicMock, MagicMock]:
    embedding = MagicMock()
    embedding.embed_query.return_value = [1.0, 0.0]
    embedding.embed.side_effect = lambda chunks: [MagicMock(vector=[0.0, 1.0]) for _ in chunks]
    vector_store = MagicMock()
    config = MemoryConfig(
        enabled=True,
        top_k=top_k,
        score_threshold=score_threshold,
        max_context_tokens=max_context_tokens,
    )
    return MemoryService(embedding, vector_store, config), embedding, vector_store


def test_load_context_returns_formatted_snippets_above_threshold() -> None:
    service, embedding, vector_store = _make_service()
    vector_store.search.return_value = [
        VectorSearchResult(
            id="r-1",
            resource_id="memory:conversation:conv-1",
            user_id="user-1",
            text="用户叫 Alice",
            metadata={},
            score=0.9,
        ),
        VectorSearchResult(
            id="r-2",
            resource_id="memory:user:user-1",
            user_id="user-1",
            text=" irrelevant ",
            metadata={},
            score=0.5,
        ),
    ]

    context = _run(service.load_context("user-1", "conv-1", "我叫什么"))

    embedding.embed_query.assert_called_once_with("我叫什么")
    vector_store.search.assert_called_once()
    assert "用户叫 Alice" in context
    assert "irrelevant" not in context
    assert vector_store.search.call_args.args[1] == 5
    assert vector_store.search.call_args.args[2] == {
        "user_id": "user-1",
        "resource_ids": [
            "memory:conversation:conv-1",
            "memory:user:user-1",
        ],
    }


def test_load_context_respects_token_budget() -> None:
    service, _, vector_store = _make_service(max_context_tokens=10)
    vector_store.search.return_value = [
        VectorSearchResult(
            id="r-1",
            resource_id="memory:conversation:conv-1",
            user_id="user-1",
            text="a" * 20,
            metadata={},
            score=0.95,
        ),
        VectorSearchResult(
            id="r-2",
            resource_id="memory:conversation:conv-1",
            user_id="user-1",
            text="b" * 20,
            metadata={},
            score=0.9,
        ),
    ]

    context = _run(service.load_context("user-1", "conv-1", "q"))
    assert "a" * 20 in context
    assert "b" * 20 not in context


def test_load_context_disabled_returns_empty() -> None:
    service, embedding, vector_store = _make_service()
    service._config.enabled = False
    assert _run(service.load_context("user-1", "conv-1", "q")) == ""
    embedding.embed_query.assert_not_called()
    vector_store.search.assert_not_called()


def test_load_context_failure_returns_empty() -> None:
    service, _, vector_store = _make_service()
    vector_store.search.side_effect = RuntimeError("vector store down")
    assert _run(service.load_context("user-1", "conv-1", "q")) == ""


def test_save_turn_upserts_conversation_memory() -> None:
    service, embedding, vector_store = _make_service()
    _run(service.save_turn("user-1", "conv-1", "我叫 Alice", "你好 Alice"))

    embedding.embed.assert_called_once()
    vector_store.upsert.assert_called_once()
    passed_records = vector_store.upsert.call_args.args[0]
    assert len(passed_records) == 1
    record = passed_records[0]
    assert isinstance(record, VectorRecord)
    assert record.resource_id == "memory:conversation:conv-1"
    assert record.user_id == "user-1"
    assert "User: 我叫 Alice" in record.text
    assert "Assistant: 你好 Alice" in record.text
    assert record.metadata["memory_type"] == "turn"


def test_save_turn_ignores_empty_question_or_answer() -> None:
    service, embedding, vector_store = _make_service()
    _run(service.save_turn("user-1", "conv-1", "", "answer"))
    _run(service.save_turn("user-1", "conv-1", "question", ""))
    embedding.embed.assert_not_called()
    vector_store.upsert.assert_not_called()


def test_save_user_facts_upserts_user_memory() -> None:
    service, embedding, vector_store = _make_service()
    _run(service.save_user_facts("user-1", ["喜欢咖啡", "养猫"]))

    embedding.embed.assert_called_once()
    vector_store.upsert.assert_called_once()
    passed_records = vector_store.upsert.call_args.args[0]
    assert len(passed_records) == 2
    assert all(r.resource_id == "memory:user:user-1" for r in passed_records)
    assert passed_records[0].metadata["memory_type"] == "user_fact"


def test_save_user_facts_ignores_empty_and_whitespace() -> None:
    service, embedding, vector_store = _make_service()
    _run(service.save_user_facts("user-1", ["", "   ", "valid"]))
    passed_records = vector_store.upsert.call_args.args[0]
    assert len(passed_records) == 1
    assert passed_records[0].text == "valid"

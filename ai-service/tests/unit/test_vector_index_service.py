from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.models.chunk import Chunk
from app.services.chunking.config import ChunkingConfig
from app.services.chunking.factory import build_chunking_service
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.service import EmbeddingService
from app.services.vector_indexing import (
    VectorIndexingConfig,
    VectorIndexService,
    build_vector_indexing_config,
)
from app.vector_store.vector_store import VectorStore

DIMENSIONS = 8


def _build_services() -> tuple[EmbeddingService, VectorStore]:
    embedding_cfg = EmbeddingConfig(
        provider="mock", model="mock", dimensions=DIMENSIONS, batch_size=4
    )
    embedding_service = EmbeddingService(
        MagicMock(),
        embedding_cfg,
    )
    embedding_service._provider.embed = MagicMock(
        side_effect=lambda texts: [[float(i)] * DIMENSIONS for i in range(len(texts))]
    )
    vector_store = MagicMock(spec=VectorStore)
    vector_store.upsert.return_value = 0
    vector_store.delete_by_resource.return_value = 0
    return embedding_service, vector_store


def _pdf_document() -> dict[str, Any]:
    return {
        "resource_id": "res-pdf",
        "total_pages": 2,
        "toc": [],
        "pages": [
            {
                "page_number": 1,
                "text": "First page paragraph one.\n\nFirst page paragraph two.",
                "blocks": [],
            },
            {
                "page_number": 2,
                "text": "Second page content.",
                "blocks": [],
            },
        ],
    }


def _asr_result() -> dict[str, Any]:
    return {
        "task_id": "task-asr",
        "resource_id": "res-asr",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Hello world"},
            {"start": 3.0, "end": 6.0, "text": "this is a test"},
        ],
        "text": "Hello world this is a test",
    }


class TestVectorIndexService:
    def test_index_pdf_deletes_existing_and_upserts_chunks(self) -> None:
        chunking_service = build_chunking_service(ChunkingConfig(chunk_size=50, chunk_overlap=5))
        embedding_service, vector_store = _build_services()
        service = VectorIndexService(chunking_service, embedding_service, vector_store)
        vector_store.upsert.return_value = 3

        count = service.index_pdf("user-1", "res-pdf", _pdf_document())

        assert count == 3
        vector_store.delete_by_resource.assert_called_once_with("res-pdf", user_id="user-1")
        upsert_call = vector_store.upsert.call_args
        records = upsert_call.args[0]
        assert len(records) == 3
        for record in records:
            assert record.user_id == "user-1"
            assert record.resource_id == "res-pdf"
            assert record.metadata["source_type"] == VectorIndexService.SOURCE_PDF
            assert "page" in record.metadata
            assert "chunk_index" in record.metadata

    def test_index_pdf_preserves_page_metadata(self) -> None:
        chunking_service = build_chunking_service(
            ChunkingConfig(chunk_size=100, chunk_overlap=5, default_strategy="paragraph")
        )
        embedding_service, vector_store = _build_services()
        vector_store.upsert.return_value = 3
        service = VectorIndexService(chunking_service, embedding_service, vector_store)

        service.index_pdf("user-1", "res-pdf", _pdf_document())

        records = vector_store.upsert.call_args.args[0]
        page_numbers = {record.metadata["page"] for record in records}
        assert page_numbers == {1, 2}
        total_pages = {record.metadata["total_pages"] for record in records}
        assert total_pages == {2}

    def test_index_pdf_skips_empty_pages(self) -> None:
        document = {
            "resource_id": "res-empty",
            "total_pages": 2,
            "toc": [],
            "pages": [
                {"page_number": 1, "text": "", "blocks": []},
                {"page_number": 2, "text": "   ", "blocks": []},
            ],
        }
        chunking_service = build_chunking_service(ChunkingConfig(chunk_size=50, chunk_overlap=5))
        embedding_service, vector_store = _build_services()
        service = VectorIndexService(chunking_service, embedding_service, vector_store)

        count = service.index_pdf("user-1", "res-empty", document)

        assert count == 0
        vector_store.delete_by_resource.assert_not_called()
        vector_store.upsert.assert_not_called()

    def test_index_pdf_uses_explicit_strategy(self) -> None:
        chunking_service = build_chunking_service(
            ChunkingConfig(chunk_size=10, chunk_overlap=0, default_strategy="paragraph")
        )
        embedding_service, vector_store = _build_services()
        service = VectorIndexService(
            chunking_service, embedding_service, vector_store, strategy="fixed_token"
        )
        vector_store.upsert.return_value = 10

        count = service.index_pdf("user-1", "res-pdf", _pdf_document())

        assert count > 0

    def test_index_asr_preserves_time_ranges(self) -> None:
        chunking_service = build_chunking_service(
            ChunkingConfig(chunk_size=50, chunk_overlap=5, default_strategy="fixed_token")
        )
        embedding_service, vector_store = _build_services()
        vector_store.upsert.return_value = 1
        service = VectorIndexService(chunking_service, embedding_service, vector_store)

        count = service.index_asr("user-2", "res-asr", _asr_result())

        assert count == 1
        records = vector_store.upsert.call_args.args[0]
        record = records[0]
        assert record.metadata["source_type"] == VectorIndexService.SOURCE_AUDIO
        assert record.metadata["start_time"] == pytest.approx(0.0, abs=0.01)
        assert record.metadata["end_time"] == pytest.approx(6.0, abs=0.01)

    def test_index_asr_returns_zero_for_empty_segments(self) -> None:
        result = {
            "task_id": "task-asr",
            "resource_id": "res-asr",
            "segments": [],
            "text": "",
        }
        chunking_service = build_chunking_service(ChunkingConfig(chunk_size=50, chunk_overlap=5))
        embedding_service, vector_store = _build_services()
        service = VectorIndexService(chunking_service, embedding_service, vector_store)

        count = service.index_asr("user-2", "res-asr", result)

        assert count == 0
        vector_store.delete_by_resource.assert_not_called()
        vector_store.upsert.assert_not_called()

    def test_index_asr_returns_zero_for_blank_text(self) -> None:
        result = {
            "task_id": "task-asr",
            "resource_id": "res-asr",
            "segments": [{"start": 0.0, "end": 1.0, "text": "   "}],
            "text": "",
        }
        chunking_service = build_chunking_service(ChunkingConfig(chunk_size=50, chunk_overlap=5))
        embedding_service, vector_store = _build_services()
        service = VectorIndexService(chunking_service, embedding_service, vector_store)

        count = service.index_asr("user-2", "res-asr", result)

        assert count == 0

    def test_upsert_chunks_calls_delete_before_upsert(self) -> None:
        chunking_service = build_chunking_service(ChunkingConfig(chunk_size=50, chunk_overlap=5))
        embedding_service, vector_store = _build_services()
        vector_store.upsert.return_value = 2
        service = VectorIndexService(chunking_service, embedding_service, vector_store)
        chunks = [
            Chunk(
                id="c-1",
                resource_id="res-1",
                index=0,
                text="hello",
                start_pos=0,
                end_pos=5,
                token_count=1,
            ),
            Chunk(
                id="c-2",
                resource_id="res-1",
                index=1,
                text="world",
                start_pos=6,
                end_pos=11,
                token_count=1,
            ),
        ]

        count = service._upsert_chunks("user-1", "res-1", chunks)

        assert count == 2
        vector_store.delete_by_resource.assert_called_once_with("res-1", user_id="user-1")
        vector_store.upsert.assert_called_once()


class TestVectorIndexingConfig:
    def test_config_defaults(self) -> None:
        cfg = build_vector_indexing_config({})
        assert cfg.enabled is True
        assert cfg.strategy is None

    def test_config_disabled(self) -> None:
        cfg = build_vector_indexing_config({"enabled": False})
        assert cfg.enabled is False

    def test_config_strategy_override(self) -> None:
        cfg = build_vector_indexing_config({"strategy": "semantic"})
        assert cfg.strategy == "semantic"

    def test_config_parses_string_boolean(self) -> None:
        cfg = build_vector_indexing_config({"enabled": "false"})
        assert cfg.enabled is False

    def test_config_object_is_immutable_value(self) -> None:
        cfg = VectorIndexingConfig(enabled=True, strategy="fixed_token")
        assert cfg.enabled is True
        assert cfg.strategy == "fixed_token"

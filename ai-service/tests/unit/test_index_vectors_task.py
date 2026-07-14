from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from celery_workers.tasks.index_vectors_task import index_resource_vectors


def _parsed_result() -> dict[str, Any]:
    return {
        "resource_id": "res-1",
        "total_pages": 1,
        "toc": [],
        "pages": [
            {"page_number": 1, "text": "hello world", "blocks": []},
        ],
    }


@patch("celery_workers.tasks.index_vectors_task.build_vector_indexing_config")
@patch("celery_workers.tasks.index_vectors_task.build_chunking_service")
@patch("celery_workers.tasks.index_vectors_task.build_embedding_service")
@patch("celery_workers.tasks.index_vectors_task.build_vector_store")
def test_index_resource_vectors_runs_pdf_pipeline(
    _mock_build_vector_store: MagicMock,
    _mock_build_embedding_service: MagicMock,
    _mock_build_chunking_service: MagicMock,
    mock_build_config: MagicMock,
) -> None:
    mock_build_config.return_value = MagicMock(enabled=True, strategy=None)
    service = MagicMock()
    service.SOURCE_PDF = "pdf"
    service.SOURCE_AUDIO = "audio"
    service.index_pdf.return_value = 3

    with patch(
        "celery_workers.tasks.index_vectors_task.VectorIndexService",
        return_value=service,
    ):
        result = index_resource_vectors.run(
            task_id="task-1",
            user_id="user-1",
            resource_id="res-1",
            source_type="pdf",
            parsed_result=_parsed_result(),
        )

    assert result == {"resource_id": "res-1", "upserted_count": 3}
    service.index_pdf.assert_called_once_with("user-1", "res-1", _parsed_result())
    service.index_asr.assert_not_called()


@patch("celery_workers.tasks.index_vectors_task.build_vector_indexing_config")
@patch("celery_workers.tasks.index_vectors_task.build_chunking_service")
@patch("celery_workers.tasks.index_vectors_task.build_embedding_service")
@patch("celery_workers.tasks.index_vectors_task.build_vector_store")
def test_index_resource_vectors_runs_asr_pipeline(
    _mock_build_vector_store: MagicMock,
    _mock_build_embedding_service: MagicMock,
    _mock_build_chunking_service: MagicMock,
    mock_build_config: MagicMock,
) -> None:
    mock_build_config.return_value = MagicMock(enabled=True, strategy=None)
    service = MagicMock()
    service.SOURCE_PDF = "pdf"
    service.SOURCE_AUDIO = "audio"
    service.index_asr.return_value = 5
    asr_result = {
        "task_id": "task-1",
        "resource_id": "res-1",
        "segments": [{"start": 0.0, "end": 1.0, "text": "hello"}],
        "text": "hello",
    }

    with patch(
        "celery_workers.tasks.index_vectors_task.VectorIndexService",
        return_value=service,
    ):
        result = index_resource_vectors.run(
            task_id="task-1",
            user_id="user-1",
            resource_id="res-1",
            source_type="audio",
            parsed_result=asr_result,
        )

    assert result == {"resource_id": "res-1", "upserted_count": 5}
    service.index_asr.assert_called_once_with("user-1", "res-1", asr_result)
    service.index_pdf.assert_not_called()


@patch("celery_workers.tasks.index_vectors_task.build_vector_indexing_config")
@patch("celery_workers.tasks.index_vectors_task.build_chunking_service")
@patch("celery_workers.tasks.index_vectors_task.build_embedding_service")
@patch("celery_workers.tasks.index_vectors_task.build_vector_store")
def test_index_resource_vectors_disabled_returns_zero(
    _mock_build_vector_store: MagicMock,
    _mock_build_embedding_service: MagicMock,
    _mock_build_chunking_service: MagicMock,
    mock_build_config: MagicMock,
) -> None:
    mock_build_config.return_value = MagicMock(enabled=False, strategy=None)

    result = index_resource_vectors.run(
        task_id="task-1",
        user_id="user-1",
        resource_id="res-1",
        source_type="pdf",
        parsed_result=_parsed_result(),
    )

    assert result == {"resource_id": "res-1", "upserted_count": 0}


@patch("celery_workers.tasks.index_vectors_task.build_vector_indexing_config")
@patch("celery_workers.tasks.index_vectors_task.build_chunking_service")
@patch("celery_workers.tasks.index_vectors_task.build_embedding_service")
@patch("celery_workers.tasks.index_vectors_task.build_vector_store")
def test_index_resource_vectors_rejects_unknown_source_type(
    _mock_build_vector_store: MagicMock,
    _mock_build_embedding_service: MagicMock,
    _mock_build_chunking_service: MagicMock,
    mock_build_config: MagicMock,
) -> None:
    mock_build_config.return_value = MagicMock(enabled=True, strategy=None)
    service = MagicMock()
    service.SOURCE_PDF = "pdf"
    service.SOURCE_AUDIO = "audio"

    with (
        patch(
            "celery_workers.tasks.index_vectors_task.VectorIndexService",
            return_value=service,
        ),
        pytest.raises(ValueError),  # noqa: PT011
    ):
        index_resource_vectors.run(
            task_id="task-1",
            user_id="user-1",
            resource_id="res-1",
            source_type="unknown",
            parsed_result={},
        )

    service.index_pdf.assert_not_called()
    service.index_asr.assert_not_called()

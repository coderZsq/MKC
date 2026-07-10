from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.core.exceptions import OcrUnavailableError, ParserUnavailableError
from app.services.ocr_service import OcrService
from celery_workers.tasks.pdf_parse_task import _build_ocr_service, run_pdf_parse


def _task_payload() -> dict[str, str]:
    return {
        "task_id": "task-1",
        "resource_id": "res-1",
        "pdf_url": "minio://resources/doc.pdf",
    }


@patch("celery_workers.tasks.pdf_parse_task._build_ocr_service")
@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_success(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    _mock_reporter_class: MagicMock,
    _mock_build_extractor: MagicMock,
    _mock_build_ocr_service: MagicMock,
) -> None:
    mock_settings.ai_config = {"pdf": {"ocr_threshold": 50}}
    expected = {
        "resource_id": "res-1",
        "total_pages": 1,
        "toc": [],
        "pages": [
            {
                "page_number": 1,
                "text": "hello",
                "blocks": [],
            },
        ],
    }
    service = MagicMock()
    service.parse.return_value = expected
    mock_service_class.return_value = service

    result = run_pdf_parse.run(task_id="task-1", payload=_task_payload())

    assert result == expected
    service.parse.assert_called_once()
    assert mock_service_class.call_args.kwargs.get("report_status") is False


@patch("celery_workers.tasks.pdf_parse_task._build_ocr_service")
@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_continues_when_ocr_unavailable(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    _mock_reporter_class: MagicMock,
    _mock_build_extractor: MagicMock,
    mock_build_ocr_service: MagicMock,
) -> None:
    mock_settings.ai_config = {"pdf": {"ocr_threshold": 50}}
    mock_build_ocr_service.side_effect = OcrUnavailableError("PaddleOCR is not installed")
    expected = {
        "resource_id": "res-1",
        "total_pages": 1,
        "toc": [],
        "pages": [
            {
                "page_number": 1,
                "text": "hello",
                "blocks": [],
            },
        ],
    }
    service = MagicMock()
    service.parse.return_value = expected
    mock_service_class.return_value = service

    result = run_pdf_parse.run(task_id="task-1", payload=_task_payload())

    assert result == expected
    service.parse.assert_called_once()
    assert mock_service_class.call_args.kwargs.get("ocr_service") is None


@patch("celery_workers.tasks.pdf_parse_task._build_ocr_service")
@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_parser_unavailable_retries(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    mock_reporter_class: MagicMock,
    mock_build_extractor: MagicMock,
    _mock_build_ocr_service: MagicMock,
) -> None:
    mock_settings.ai_config = {"pdf": {}}
    mock_build_extractor.side_effect = ParserUnavailableError("PyMuPDF missing")

    run_pdf_parse.request.retries = 0
    run_pdf_parse.request.max_retries = 3

    retry_mock = MagicMock(return_value=Retry())
    with patch.object(run_pdf_parse, "retry", retry_mock), pytest.raises(Retry):
        run_pdf_parse.run(task_id="task-1", payload=_task_payload())

    retry_mock.assert_called_once_with(kwargs={"task_id": "task-1", "payload": _task_payload()})
    mock_reporter_class.return_value.mark_status.assert_any_call(
        "task-1",
        "running",
        attempt_count=1,
    )


@patch("celery_workers.tasks.pdf_parse_task._build_ocr_service")
@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_parser_unavailable_exhausted(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    mock_reporter_class: MagicMock,
    mock_build_extractor: MagicMock,
    _mock_build_ocr_service: MagicMock,
) -> None:
    mock_settings.ai_config = {"pdf": {}}
    mock_build_extractor.side_effect = ParserUnavailableError("PyMuPDF missing")
    reporter = MagicMock()
    mock_reporter_class.return_value = reporter

    run_pdf_parse.request.retries = 3
    run_pdf_parse.request.max_retries = 3

    with pytest.raises(ParserUnavailableError):
        run_pdf_parse.run(task_id="task-1", payload=_task_payload())

    reporter.mark_status.assert_any_call(
        "task-1",
        "running",
        attempt_count=4,
    )
    reporter.mark_status.assert_any_call(
        "task-1",
        "failed",
        error_message="PyMuPDF missing",
        attempt_count=4,
    )


@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_build_ocr_service_returns_none_when_disabled(mock_settings: MagicMock) -> None:
    mock_settings.ai_config = {"ocr": {"enabled": False}}

    service = _build_ocr_service()

    assert service is None


@patch("celery_workers.tasks.pdf_parse_task.PaddleOCREngine")
@patch("celery_workers.tasks.pdf_parse_task.PdfRenderer")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_build_ocr_service_returns_service_when_enabled(
    mock_settings: MagicMock,
    mock_renderer_class: MagicMock,
    mock_engine_class: MagicMock,
) -> None:
    mock_settings.ai_config = {
        "ocr": {
            "enabled": True,
            "lang": "en",
            "dpi": 200,
            "max_pages_in_memory": 3,
            "use_gpu": True,
        },
    }
    mock_engine_class.return_value = MagicMock()
    mock_renderer_class.return_value = MagicMock()

    service = _build_ocr_service()

    assert isinstance(service, OcrService)
    mock_engine_class.assert_called_once_with(lang="en", use_gpu=True)
    mock_renderer_class.assert_called_once_with(dpi=200)


@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_build_ocr_service_raises_for_unsupported_engine(mock_settings: MagicMock) -> None:
    mock_settings.ai_config = {"ocr": {"enabled": True, "engine": "tesseract"}}

    with pytest.raises(OcrUnavailableError):
        _build_ocr_service()


@patch("celery_workers.tasks.pdf_parse_task.PaddleOCREngine")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_build_ocr_service_wraps_engine_error_as_unavailable(
    mock_settings: MagicMock,
    mock_engine_class: MagicMock,
) -> None:
    mock_settings.ai_config = {"ocr": {"enabled": True, "engine": "paddleocr"}}
    mock_engine_class.side_effect = RuntimeError("dll load failed")

    with pytest.raises(OcrUnavailableError):
        _build_ocr_service()

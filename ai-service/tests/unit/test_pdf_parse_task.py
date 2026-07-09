from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.exceptions import ParserUnavailableError
from celery_workers.tasks.pdf_parse_task import run_pdf_parse


def _task_payload() -> dict[str, str]:
    return {
        "task_id": "task-1",
        "resource_id": "res-1",
        "pdf_url": "minio://resources/doc.pdf",
    }


@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_success(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    _mock_reporter_class: MagicMock,
    _mock_build_extractor: MagicMock,
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
    service.parse.return_value = MagicMock(model_dump=MagicMock(return_value=expected))
    mock_service_class.return_value = service

    result = run_pdf_parse.run(task_id="task-1", payload=_task_payload())

    assert result == expected
    service.parse.assert_called_once()


@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_parser_unavailable_retries(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    _mock_reporter_class: MagicMock,
    mock_build_extractor: MagicMock,
) -> None:
    mock_settings.ai_config = {"pdf": {}}
    mock_build_extractor.side_effect = ParserUnavailableError("PyMuPDF missing")

    run_pdf_parse.request.retries = 0
    run_pdf_parse.request.max_retries = 3

    retry_mock = MagicMock()
    retry_mock.side_effect = Exception("retry scheduled")
    with patch.object(run_pdf_parse, "retry", retry_mock):
        try:
            run_pdf_parse.run(task_id="task-1", payload=_task_payload())
        except Exception as exc:
            if "retry scheduled" not in str(exc):
                raise

    retry_mock.assert_called_once()


@patch("celery_workers.tasks.pdf_parse_task._build_extractor")
@patch("celery_workers.tasks.pdf_parse_task.GatewayProgressReporter")
@patch("celery_workers.tasks.pdf_parse_task.PdfParserService")
@patch("celery_workers.tasks.pdf_parse_task.settings")
def test_run_pdf_parse_parser_unavailable_exhausted(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    mock_reporter_class: MagicMock,
    mock_build_extractor: MagicMock,
) -> None:
    mock_settings.ai_config = {"pdf": {}}
    mock_build_extractor.side_effect = ParserUnavailableError("PyMuPDF missing")
    reporter = MagicMock()
    mock_reporter_class.return_value = reporter

    run_pdf_parse.request.retries = 3
    run_pdf_parse.request.max_retries = 3

    try:
        run_pdf_parse.run(task_id="task-1", payload=_task_payload())
    except ParserUnavailableError:
        pass
    else:
        raise AssertionError("expected ParserUnavailableError to be raised")

    reporter.mark_status.assert_called_once_with(
        "task-1",
        "failed",
        error_message="PyMuPDF missing",
    )

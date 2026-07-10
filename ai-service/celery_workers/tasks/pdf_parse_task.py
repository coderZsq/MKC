from __future__ import annotations

import logging
from typing import Any

from celery import Task

from app.core.config import settings
from app.core.exceptions import OcrUnavailableError, ParserUnavailableError
from app.models.pdf import PdfParseTask
from app.services.gateway_reporter import GatewayProgressReporter
from app.services.minio_storage import download_file, upload_json
from app.services.ocr_service import OcrService
from app.services.paddle_ocr_engine import PaddleOCREngine
from app.services.pdf_parser_service import PdfParserService
from app.services.pymupdf_extractor import PyMuPDFExtractor
from app.utils.pdf_renderer import PdfRenderer
from celery_workers.celery_app import celery_app
from celery_workers.tasks.base import BaseAITask

logger = logging.getLogger(__name__)


def _build_extractor() -> PyMuPDFExtractor:
    pdf_cfg = (settings.ai_config or {}).get("pdf", {})
    try:
        return PyMuPDFExtractor(
            ocr_threshold=pdf_cfg.get("ocr_threshold", 50),
        )
    except ImportError as exc:
        raise ParserUnavailableError("PyMuPDF is not installed") from exc


def _build_ocr_service() -> OcrService | None:
    ocr_cfg = (settings.ai_config or {}).get("ocr", {})
    if not ocr_cfg.get("enabled", True):
        return None

    engine_name = ocr_cfg.get("engine", "paddleocr")
    if engine_name != "paddleocr":
        raise OcrUnavailableError(f"Unsupported OCR engine: {engine_name}")

    try:
        engine = PaddleOCREngine(
            lang=ocr_cfg.get("lang", "ch"),
            use_gpu=ocr_cfg.get("use_gpu", False),
        )
        renderer = PdfRenderer(dpi=ocr_cfg.get("dpi", 300))
    except OcrUnavailableError:
        raise
    except Exception as exc:
        raise OcrUnavailableError(f"OCR engine is unavailable: {exc}") from exc

    return OcrService(
        renderer=renderer,
        engine=engine,
        max_pages_in_memory=ocr_cfg.get("max_pages_in_memory", 5),
    )


@celery_app.task(bind=True, base=BaseAITask)
def run_pdf_parse(self: Task, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Celery task that extracts text from a PDF and reports the result.

    Automatic retry and exponential backoff are handled by :class:`BaseAITask`.
    """
    task = PdfParseTask.model_validate(payload)
    pdf_cfg = (settings.ai_config or {}).get("pdf", {})

    reporter = GatewayProgressReporter()
    reporter.mark_status(task_id, "running", attempt_count=self._attempt_count())

    retry_payload = payload
    try:
        extractor = _build_extractor()
        try:
            ocr_service = _build_ocr_service()
        except OcrUnavailableError as exc:
            logger.warning("OCR unavailable, disabling OCR fallback: %s", exc)
            ocr_service = None
        service = PdfParserService(
            extractor=extractor,
            reporter=reporter,
            download_func=download_file,
            upload_func=upload_json,
            ocr_service=ocr_service,
            progress_interval=pdf_cfg.get("progress_interval", 5.0),
            ocr_fallback=pdf_cfg.get("ocr_fallback", True),
            ocr_threshold=pdf_cfg.get("ocr_threshold", 50),
            max_pdf_size=pdf_cfg.get("max_pdf_size", 104_857_600),
            max_pages=pdf_cfg.get("max_pages", 5_000),
            report_status=False,
        )
        document = service.parse(task)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            reporter.mark_status(
                task_id,
                "failed",
                error_message=str(exc),
                attempt_count=self._attempt_count(),
            )
            self._failure_reported = True
            raise
        retry_exc = exc
    else:
        return document.model_dump()

    raise self.retry(args=[task_id, retry_payload], exc=retry_exc)

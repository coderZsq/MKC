from __future__ import annotations

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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def run_pdf_parse(self: Task, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Celery task that extracts text from a PDF and reports the result."""
    task = PdfParseTask.model_validate(payload)
    pdf_cfg = (settings.ai_config or {}).get("pdf", {})

    try:
        extractor = _build_extractor()
        ocr_service = _build_ocr_service()
        reporter = GatewayProgressReporter()
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
        )
        document = service.parse(task)
    except ParserUnavailableError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)  # noqa: B904
        GatewayProgressReporter().mark_status(task_id, "failed", error_message=exc.message)
        raise

    return document.model_dump()

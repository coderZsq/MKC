from __future__ import annotations

import logging
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from app.core.exceptions import (
    CorruptPdfError,
    EncryptedPdfError,
    NoTextLayerError,
    OcrNoTextError,
    OcrPageFailedError,
    OcrUnavailableError,
    PdfNotFoundError,
    PdfParseError,
)
from app.models.pdf import PdfDocument, PdfParseTask
from app.services.gateway_reporter import GatewayProgressReporter
from app.services.ocr_service import OcrService
from app.services.pymupdf_extractor import detect_no_text_layer, is_scanned_page

logger = logging.getLogger(__name__)


class _PdfExtractor(Protocol):
    def extract(self, pdf_path: Path, resource_id: str = "") -> PdfDocument: ...


def _default_download(_url: str, _target: Path) -> None:
    raise PdfNotFoundError("no download function configured")


def _default_upload(_data: dict[str, Any], _key: str) -> str:
    raise PdfParseError("no upload function configured")


def _safe_task_id(task_id: str) -> str:
    """Sanitize ``task_id`` so it can be used safely in a MinIO key."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", task_id) or "unknown"


class PdfParserService:
    """Orchestrates PDF download, extraction, result upload and reporting."""

    def __init__(
        self,
        extractor: _PdfExtractor,
        reporter: GatewayProgressReporter,
        download_func: Callable[[str, Path], None] | None = None,
        upload_func: Callable[[dict[str, Any], str], str] | None = None,
        ocr_service: OcrService | None = None,
        progress_interval: float = 5.0,
        ocr_fallback: bool = True,
        ocr_threshold: int = 50,
        max_pdf_size: int = 104_857_600,
        max_pages: int = 5_000,
    ) -> None:
        self._extractor = extractor
        self._reporter = reporter
        self._download_func = download_func or _default_download
        self._upload_func = upload_func or _default_upload
        self._ocr_service = ocr_service
        self._progress_interval = progress_interval
        self._ocr_fallback = ocr_fallback
        self._ocr_threshold = ocr_threshold
        self._max_pdf_size = max_pdf_size
        self._max_pages = max_pages

    def parse(self, task: PdfParseTask) -> PdfDocument:
        """Download, extract, upload and report the result for a task."""
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                pdf_path = Path(tmp_dir) / "source.pdf"
                self._download_func(task.pdf_url, pdf_path)
                self._enforce_size_limit(pdf_path)
                self._reporter.mark_status(task.task_id, "running")
                document = self._extract_and_report(task, pdf_path)
                result = self._build_result(task, document)
                self._reporter.mark_status(
                    task.task_id,
                    "completed",
                    result=result,
                )
                return document
        except PdfNotFoundError as exc:
            logger.error("PDF not found for task %s: %s", task.task_id, exc)
            self._reporter.mark_status(
                task.task_id,
                "failed",
                error_message=exc.message,
            )
            raise
        except (
            EncryptedPdfError,
            CorruptPdfError,
            NoTextLayerError,
            PdfParseError,
            OcrUnavailableError,
            OcrPageFailedError,
            OcrNoTextError,
        ) as exc:
            logger.error(
                "PDF extraction failed for task %s: %s",
                task.task_id,
                exc,
            )
            self._reporter.mark_status(
                task.task_id,
                "failed",
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            logger.exception("unexpected error during PDF parse for task %s", task.task_id)
            self._reporter.mark_status(
                task.task_id,
                "failed",
                error_message="PDF parse failed unexpectedly",
            )
            raise PdfParseError("PDF parse failed unexpectedly") from exc

    def _enforce_size_limit(self, pdf_path: Path) -> None:
        size = pdf_path.stat().st_size
        if size > self._max_pdf_size:
            raise PdfParseError(f"PDF exceeds maximum allowed size of {self._max_pdf_size} bytes")

    def _extract_and_report(self, task: PdfParseTask, pdf_path: Path) -> PdfDocument:
        """Extract the document and report progress page by page.

        When every page looks scanned and OCR fallback is enabled, the PDF is
        re-processed through the configured OCR service.
        """
        extracted = self._extractor.extract(pdf_path, resource_id=task.resource_id)
        if extracted.total_pages > self._max_pages:
            raise PdfParseError(f"PDF exceeds maximum allowed page count of {self._max_pages}")

        document = self._apply_ocr_fallback(task, pdf_path, extracted)
        total_pages = document.total_pages
        last_reported = 0

        for index, _page in enumerate(document.pages):
            progress = self._page_progress(index, total_pages)
            if progress - last_reported >= self._progress_interval or progress >= 100:
                self._reporter.report_progress(task.task_id, progress, "running")
                last_reported = progress

        return document

    def _apply_ocr_fallback(
        self,
        task: PdfParseTask,
        pdf_path: Path,
        extracted: PdfDocument,
    ) -> PdfDocument:
        """Return the OCR document when the extracted document has no text layer."""
        if not self._ocr_fallback:
            return extracted

        if not self._is_fully_scanned(extracted):
            return extracted

        if self._ocr_service is None:
            detect_no_text_layer(extracted, self._ocr_threshold)
            return extracted

        def _report_ocr_progress(progress: int) -> None:
            self._reporter.report_progress(task.task_id, progress, "running")

        return self._ocr_service.process_pdf(
            pdf_path,
            resource_id=task.resource_id,
            progress_callback=_report_ocr_progress,
        )

    def _is_fully_scanned(self, document: PdfDocument) -> bool:
        if not document.pages:
            return False
        return all(
            is_scanned_page(page.text, threshold=self._ocr_threshold) for page in document.pages
        )

    @staticmethod
    def _page_progress(page_index: int, total_pages: int) -> int:
        if total_pages <= 0:
            return 100
        return int(min((page_index + 1) / total_pages * 100, 100))

    def _build_result(
        self,
        task: PdfParseTask,
        document: PdfDocument,
    ) -> dict[str, Any]:
        """Upload the parsed JSON and return the result payload for Gateway."""
        safe_id = _safe_task_id(task.task_id)
        key = f"results/{safe_id}/parsed.json"
        data = document.model_dump()
        parsed_url = self._upload_func(data, key)
        data["parsed_url"] = parsed_url
        return data

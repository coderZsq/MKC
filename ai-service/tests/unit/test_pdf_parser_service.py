from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    CorruptPdfError,
    EncryptedPdfError,
    NoTextLayerError,
    OcrNoTextError,
    OcrPageFailedError,
    OcrUnavailableError,
    PdfParseError,
)
from app.models.pdf import PdfBlock, PdfDocument, PdfPage, PdfParseTask, PdfTocEntry
from app.services.ocr_service import OcrService
from app.services.pdf_parser_service import PdfParserService


class TestPdfParserService:
    @pytest.fixture
    def fake_extractor(self) -> MagicMock:
        extractor = MagicMock()
        extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=2,
            toc=[PdfTocEntry(level=1, title="Intro", page=1)],
            pages=[
                PdfPage(
                    page_number=1,
                    text="Page one text content is long enough to pass the scan detection threshold.",
                    blocks=[PdfBlock(x=0, y=0, width=10, height=10, text="block")],
                ),
                PdfPage(
                    page_number=2,
                    text="Page two text content is also long enough to avoid being flagged as scanned.",
                    blocks=[],
                ),
            ],
        )
        return extractor

    @pytest.fixture
    def fake_reporter(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> PdfParserService:
        return PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "minio://mkc-resources/results/task-1/parsed.json",
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )

    def test_parse_success(self, service: PdfParserService, fake_reporter: MagicMock) -> None:
        task = PdfParseTask(
            task_id="task-1",
            resource_id="res-1",
            pdf_url="minio://resources/doc.pdf",
        )

        result = service.parse(task)

        assert result["resource_id"] == "res-1"
        assert result["total_pages"] == 2
        assert len(result["pages"]) == 2
        fake_reporter.mark_status.assert_any_call("task-1", "running")
        completed_call = fake_reporter.mark_status.call_args_list[-1]
        assert completed_call.args[1] == "completed"
        result_payload = completed_call.kwargs["result"]
        assert result_payload["total_pages"] == 2
        assert result_payload["pages"][0]["page_number"] == 1
        assert result_payload["parsed_url"] == "minio://mkc-resources/results/task-1/parsed.json"

    def test_report_status_false_skips_status_reports(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "minio://mkc-resources/results/task-1/parsed.json",
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
            report_status=False,
        )
        task = PdfParseTask(
            task_id="task-1",
            resource_id="res-1",
            pdf_url="minio://resources/doc.pdf",
        )

        result = service.parse(task)

        assert result["total_pages"] == 2
        fake_reporter.mark_status.assert_not_called()

    def test_progress_reported_for_each_page(
        self,
        service: PdfParserService,
        fake_reporter: MagicMock,
    ) -> None:
        task = PdfParseTask(
            task_id="task-1",
            resource_id="res-1",
            pdf_url="minio://resources/doc.pdf",
        )

        service.parse(task)

        progress_calls = list(fake_reporter.report_progress.call_args_list)
        assert len(progress_calls) == 2
        assert progress_calls[0].args == ("task-1", 50, "running")
        assert progress_calls[1].args == ("task-1", 100, "running")

    def test_scanned_pdf_raises_no_text_layer(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[
                PdfPage(page_number=1, text="", blocks=[]),
            ],
        )
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "minio://mkc-resources/results/task-1/parsed.json",
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-1",
            resource_id="res-1",
            pdf_url="minio://resources/scanned.pdf",
        )

        with pytest.raises(NoTextLayerError):
            service.parse(task)

        fake_reporter.mark_status.assert_called_with(
            "task-1",
            "failed",
            error_message=NoTextLayerError().message,
        )

    def test_encrypted_pdf_reports_failed(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.side_effect = EncryptedPdfError()
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-2",
            resource_id="res-2",
            pdf_url="minio://resources/encrypted.pdf",
        )

        with pytest.raises(EncryptedPdfError):
            service.parse(task)

        fake_reporter.mark_status.assert_called_with(
            "task-2",
            "failed",
            error_message=EncryptedPdfError().message,
        )

    def test_download_failure_reports_failed(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        from app.core.exceptions import PdfNotFoundError

        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, _target: (_ for _ in ()).throw(PdfNotFoundError("missing")),
            upload_func=lambda _data, _key: "",
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-3",
            resource_id="res-3",
            pdf_url="minio://resources/missing.pdf",
        )

        with pytest.raises(PdfNotFoundError):
            service.parse(task)

        fake_reporter.mark_status.assert_called_with(
            "task-3",
            "failed",
            error_message="missing",
        )

    def test_unexpected_error_reports_failed(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.side_effect = CorruptPdfError("boom")
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-4",
            resource_id="res-4",
            pdf_url="minio://resources/bad.pdf",
        )

        with pytest.raises(CorruptPdfError):
            service.parse(task)

        fake_reporter.mark_status.assert_called_with(
            "task-4",
            "failed",
            error_message="boom",
        )

    def test_task_id_sanitized_in_result_key(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, key: key,
            progress_interval=0.0,
            ocr_fallback=False,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-1/../../evil",
            resource_id="res-1",
            pdf_url="minio://resources/doc.pdf",
        )

        service.parse(task)
        completed_call = fake_reporter.mark_status.call_args_list[-1]
        result = completed_call.kwargs["result"]
        assert result["parsed_url"] == "results/task-1evil/parsed.json"

    def test_pdf_size_limit_enforced(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            progress_interval=0.0,
            ocr_fallback=False,
            ocr_threshold=50,
            max_pdf_size=1,
        )
        task = PdfParseTask(
            task_id="task-size",
            resource_id="res-1",
            pdf_url="minio://resources/doc.pdf",
        )

        with pytest.raises(PdfParseError, match="exceeds maximum allowed size"):
            service.parse(task)

        fake_reporter.mark_status.assert_called_with(
            "task-size",
            "failed",
            error_message="PDF exceeds maximum allowed size of 1 bytes",
        )

    def test_pdf_page_limit_enforced(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=10,
            toc=[],
            pages=[
                PdfPage(
                    page_number=i,
                    text="Some text content that is long enough to avoid scan detection.",
                    blocks=[],
                )
                for i in range(1, 11)
            ],
        )
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            progress_interval=0.0,
            ocr_fallback=False,
            ocr_threshold=50,
            max_pages=5,
        )
        task = PdfParseTask(
            task_id="task-pages",
            resource_id="res-1",
            pdf_url="minio://resources/doc.pdf",
        )

        with pytest.raises(PdfParseError, match="exceeds maximum allowed page count"):
            service.parse(task)

        fake_reporter.mark_status.assert_called_with(
            "task-pages",
            "failed",
            error_message="PDF exceeds maximum allowed page count of 5",
        )

    def test_ocr_disabled_skips_scan_check(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[PdfPage(page_number=1, text="", blocks=[])],
        )
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "minio://mkc-resources/results/task-1/parsed.json",
            progress_interval=0.0,
            ocr_fallback=False,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-5",
            resource_id="res-5",
            pdf_url="minio://resources/scanned.pdf",
        )

        document = service.parse(task)
        assert document["total_pages"] == 1
        completed_call = fake_reporter.mark_status.call_args_list[-1]
        assert completed_call.args[1] == "completed"
        assert (
            completed_call.kwargs["result"]["parsed_url"]
            == "minio://mkc-resources/results/task-1/parsed.json"
        )

    def test_scanned_pdf_triggers_ocr_fallback(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[PdfPage(page_number=1, text="", blocks=[])],
        )
        ocr_document = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[
                PdfPage(
                    page_number=1,
                    text="OCR text",
                    blocks=[
                        PdfBlock(
                            x=0,
                            y=0,
                            width=10,
                            height=10,
                            text="OCR text",
                            confidence=0.91,
                        ),
                    ],
                ),
            ],
        )
        ocr_service = MagicMock(spec=OcrService)
        ocr_service.process_pdf.return_value = ocr_document
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "minio://mkc-resources/results/task-1/parsed.json",
            ocr_service=ocr_service,
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-ocr",
            resource_id="res-1",
            pdf_url="minio://resources/scanned.pdf",
        )

        document = service.parse(task)

        assert document["pages"][0]["text"] == "OCR text"
        assert (
            document["parsed_url"]
            == "minio://mkc-resources/results/task-1/parsed.json"
        )
        ocr_service.process_pdf.assert_called_once()
        completed_call = fake_reporter.mark_status.call_args_list[-1]
        result = completed_call.kwargs["result"]
        assert result["pages"][0]["blocks"][0]["confidence"] == pytest.approx(0.91)

    def test_ocr_unavailable_error_is_reported(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[PdfPage(page_number=1, text="", blocks=[])],
        )
        ocr_service = MagicMock(spec=OcrService)
        ocr_service.process_pdf.side_effect = OcrUnavailableError("OCR not ready")
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            ocr_service=ocr_service,
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-ocr-unavailable",
            resource_id="res-1",
            pdf_url="minio://resources/scanned.pdf",
        )

        with pytest.raises(OcrUnavailableError) as exc_info:
            service.parse(task)

        assert exc_info.value.status_code == 503
        fake_reporter.mark_status.assert_called_with(
            "task-ocr-unavailable",
            "failed",
            error_message="OCR not ready",
        )

    def test_ocr_no_text_error_is_reported(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[PdfPage(page_number=1, text="", blocks=[])],
        )
        ocr_service = MagicMock(spec=OcrService)
        ocr_service.process_pdf.side_effect = OcrNoTextError()
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            ocr_service=ocr_service,
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-ocr-empty",
            resource_id="res-1",
            pdf_url="minio://resources/scanned.pdf",
        )

        with pytest.raises(OcrNoTextError) as exc_info:
            service.parse(task)

        assert exc_info.value.status_code == 400
        fake_reporter.mark_status.assert_called_with(
            "task-ocr-empty",
            "failed",
            error_message=OcrNoTextError().message,
        )

    def test_ocr_page_failed_error_is_reported(
        self,
        fake_extractor: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_extractor.extract.return_value = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[PdfPage(page_number=1, text="", blocks=[])],
        )
        ocr_service = MagicMock(spec=OcrService)
        ocr_service.process_pdf.side_effect = OcrPageFailedError("page 1 failed")
        service = PdfParserService(
            extractor=fake_extractor,
            reporter=fake_reporter,
            download_func=lambda _url, target: Path(target).write_bytes(b"pdf"),
            upload_func=lambda _data, _key: "",
            ocr_service=ocr_service,
            progress_interval=0.0,
            ocr_fallback=True,
            ocr_threshold=50,
        )
        task = PdfParseTask(
            task_id="task-ocr-page",
            resource_id="res-1",
            pdf_url="minio://resources/scanned.pdf",
        )

        with pytest.raises(OcrPageFailedError) as exc_info:
            service.parse(task)

        assert exc_info.value.status_code == 500

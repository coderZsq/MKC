from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import OcrNoTextError, OcrPageFailedError
from app.models.pdf import PdfBlock, PdfDocument
from app.services.ocr_service import OcrService
from app.utils.pdf_renderer import PdfRenderer, RenderPage


def _render_page(page_number: int, total_pages: int, image_path: Path) -> RenderPage:
    return RenderPage(
        page_number=page_number,
        total_pages=total_pages,
        image_path=image_path,
    )


class _FakeEngine:
    def __init__(self, blocks_by_page: dict[int, list[PdfBlock]]) -> None:
        self._blocks_by_page = blocks_by_page

    def recognize(self, _image_path: Path) -> list[PdfBlock]:
        page_index = getattr(self, "_current_page", 0)
        self._current_page = page_index + 1
        return list(self._blocks_by_page.get(page_index, []))


class TestOcrService:
    def test_process_pdf_returns_structured_document(self) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        renderer.render_pages.return_value = iter(
            [
                _render_page(1, 2, Path("/tmp/page_1.png")),
                _render_page(2, 2, Path("/tmp/page_2.png")),
            ]
        )
        blocks = [
            PdfBlock(x=0, y=0, width=10, height=10, text="First", confidence=0.9),
            PdfBlock(x=0, y=20, width=10, height=10, text="page", confidence=0.8),
        ]
        engine = _FakeEngine({0: blocks, 1: []})
        service = OcrService(renderer=renderer, engine=engine)

        document = service.process_pdf(Path("/tmp/doc.pdf"), resource_id="res-1")

        assert isinstance(document, PdfDocument)
        assert document.resource_id == "res-1"
        assert document.total_pages == 2
        assert len(document.pages) == 2
        assert document.pages[0].page_number == 1
        assert "First\npage" in document.pages[0].text
        assert len(document.pages[0].blocks) == 2
        assert document.pages[1].text == ""

    def test_process_pdf_raises_when_all_pages_blank(self) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        renderer.render_pages.return_value = iter([_render_page(1, 1, Path("/tmp/page_1.png"))])
        engine = _FakeEngine({0: []})
        service = OcrService(renderer=renderer, engine=engine)

        with pytest.raises(OcrNoTextError):
            service.process_pdf(Path("/tmp/doc.pdf"))

    def test_process_pdf_continues_when_single_page_fails(self) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        renderer.render_pages.return_value = iter(
            [
                _render_page(1, 2, Path("/tmp/page_1.png")),
                _render_page(2, 2, Path("/tmp/page_2.png")),
            ]
        )

        class FailingEngine:
            def __init__(self) -> None:
                self._page = 0

            def recognize(self, _image_path: Path) -> list[PdfBlock]:
                page = self._page
                self._page += 1
                if page == 0:
                    raise OcrPageFailedError("mock failure")
                return [PdfBlock(x=0, y=0, width=10, height=10, text="OK", confidence=0.9)]

        service = OcrService(renderer=renderer, engine=FailingEngine())

        document = service.process_pdf(Path("/tmp/doc.pdf"))

        assert document.total_pages == 2
        assert document.pages[0].text == ""
        assert document.pages[1].text == "OK"

    def test_process_pdf_reports_empty_document_as_no_text(self) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        renderer.render_pages.return_value = iter([])
        engine = _FakeEngine({})
        service = OcrService(renderer=renderer, engine=engine)

        with pytest.raises(OcrNoTextError):
            service.process_pdf(Path("/tmp/doc.pdf"))

    def test_process_pdf_sorts_blocks_by_reading_order(self) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        renderer.render_pages.return_value = iter([_render_page(1, 1, Path("/tmp/page_1.png"))])
        blocks = [
            PdfBlock(x=0, y=30, width=10, height=10, text="third", confidence=0.9),
            PdfBlock(x=0, y=0, width=10, height=10, text="first", confidence=0.9),
            PdfBlock(x=20, y=0, width=10, height=10, text="second", confidence=0.9),
        ]
        engine = _FakeEngine({0: blocks})
        service = OcrService(renderer=renderer, engine=engine)

        document = service.process_pdf(Path("/tmp/doc.pdf"))

        assert document.pages[0].text == "first\nsecond\nthird"
        assert [block.text for block in document.pages[0].blocks] == [
            "first",
            "second",
            "third",
        ]

    def test_process_pdf_deletes_rendered_images_after_ocr(self, tmp_path: Path) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        image_paths = [tmp_path / "page_0.png", tmp_path / "page_1.png"]
        for path in image_paths:
            path.write_text("png")
        renderer.render_pages.return_value = iter(
            [
                _render_page(1, 2, image_paths[0]),
                _render_page(2, 2, image_paths[1]),
            ]
        )
        engine = _FakeEngine({0: [], 1: []})
        service = OcrService(renderer=renderer, engine=engine, max_pages_in_memory=1)

        with pytest.raises(OcrNoTextError):
            service.process_pdf(tmp_path / "doc.pdf")

        assert all(not path.exists() for path in image_paths)

    def test_process_pdf_calls_progress_callback(self) -> None:
        renderer = MagicMock(spec=PdfRenderer)
        renderer.render_pages.return_value = iter(
            [
                _render_page(1, 2, Path("/tmp/page_1.png")),
                _render_page(2, 2, Path("/tmp/page_2.png")),
            ]
        )
        engine = _FakeEngine({0: [], 1: []})
        service = OcrService(renderer=renderer, engine=engine)
        progress: list[int] = []

        with pytest.raises(OcrNoTextError):
            service.process_pdf(
                Path("/tmp/doc.pdf"),
                progress_callback=progress.append,
            )

        assert progress == [50, 100]

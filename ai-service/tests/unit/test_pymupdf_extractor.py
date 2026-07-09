from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path

import pytest

from app.core.exceptions import CorruptPdfError, EncryptedPdfError
from app.models.pdf import PdfDocument, PdfPage
from app.services.pymupdf_extractor import (
    PyMuPDFExtractor,
    detect_no_text_layer,
    is_scanned_page,
)


def _make_text_pdf() -> Path:
    """Create a temporary PDF with two pages, text and a TOC."""
    import fitz

    tmp_dir = tempfile.mkdtemp()
    pdf_path = Path(tmp_dir) / "test.pdf"
    doc = fitz.open()

    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((50, 100), "Hello World")
    page1.insert_text((50, 200), "Second block")

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((50, 100), "Page two content")

    doc.set_toc([(1, "Chapter 1", 1), (2, "Chapter 2", 2)])
    doc.save(str(pdf_path))
    doc.close()

    def _cleanup() -> None:
        pdf_path.unlink(missing_ok=True)
        Path(tmp_dir).rmdir()

    # Keep a reference for cleanup if needed; pytest tmp cleanup is not used here.
    _make_text_pdf._last_path = pdf_path  # type: ignore[attr-defined]
    return pdf_path


def _make_empty_pdf() -> Path:
    """Create a temporary PDF with one blank page (no text)."""
    import fitz

    tmp_dir = tempfile.mkdtemp()
    pdf_path = Path(tmp_dir) / "empty.pdf"
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(str(pdf_path))
    doc.close()
    _make_empty_pdf._last_path = pdf_path  # type: ignore[attr-defined]
    return pdf_path


def _make_encrypted_pdf() -> Path:
    """Create a temporary password-protected PDF."""
    import fitz

    tmp_dir = tempfile.mkdtemp()
    pdf_path = Path(tmp_dir) / "encrypted.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 100), "Secret")
    doc.save(str(pdf_path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret")
    doc.close()
    _make_encrypted_pdf._last_path = pdf_path  # type: ignore[attr-defined]
    return pdf_path


@pytest.fixture(autouse=True)
def _cleanup_pdf_fixtures() -> None:
    """Remove temporary PDFs created by helper functions."""
    yield
    for helper in (_make_text_pdf, _make_empty_pdf, _make_encrypted_pdf):
        path = getattr(helper, "_last_path", None)
        if path is not None:
            path.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                path.parent.rmdir()


class TestPyMuPDFExtractor:
    @pytest.fixture
    def extractor(self) -> PyMuPDFExtractor:
        return PyMuPDFExtractor(ocr_threshold=50)

    def test_extract_text_per_page(self, extractor: PyMuPDFExtractor) -> None:
        pdf_path = _make_text_pdf()
        document = extractor.extract(pdf_path, resource_id="res-1")

        assert document.total_pages == 2
        assert len(document.pages) == 2
        assert "Hello World" in document.pages[0].text
        assert "Page two content" in document.pages[1].text

    def test_page_numbers_start_at_one(self, extractor: PyMuPDFExtractor) -> None:
        pdf_path = _make_text_pdf()
        document = extractor.extract(pdf_path, resource_id="res-1")

        assert document.pages[0].page_number == 1
        assert document.pages[1].page_number == 2

    def test_extract_toc(self, extractor: PyMuPDFExtractor) -> None:
        pdf_path = _make_text_pdf()
        document = extractor.extract(pdf_path, resource_id="res-1")

        assert len(document.toc) == 2
        assert document.toc[0].level == 1
        assert document.toc[0].title == "Chapter 1"
        assert document.toc[0].page == 1

    def test_extract_blocks_with_coordinates(self, extractor: PyMuPDFExtractor) -> None:
        pdf_path = _make_text_pdf()
        document = extractor.extract(pdf_path, resource_id="res-1")

        page = document.pages[0]
        assert len(page.blocks) >= 2
        block = page.blocks[0]
        assert block.x >= 0
        assert block.y >= 0
        assert block.width >= 0
        assert block.height >= 0
        assert block.text.strip()

    def test_encrypted_pdf_raises(self, extractor: PyMuPDFExtractor) -> None:
        pdf_path = _make_encrypted_pdf()
        with pytest.raises(EncryptedPdfError):
            extractor.extract(pdf_path)

    def test_corrupt_pdf_raises(self, extractor: PyMuPDFExtractor) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "corrupt.pdf"
            pdf_path.write_bytes(b"not a pdf")
            with pytest.raises(CorruptPdfError):
                extractor.extract(pdf_path)

    def test_empty_pdf_returns_zero_pages(self, extractor: PyMuPDFExtractor) -> None:
        pdf_path = _make_empty_pdf()
        document = extractor.extract(pdf_path, resource_id="res-1")

        assert document.total_pages == 1
        assert document.pages[0].text == ""
        assert document.pages[0].blocks == []


class TestScanDetection:
    def test_is_scanned_page_empty_text(self) -> None:
        assert is_scanned_page("", threshold=50) is True
        assert is_scanned_page("   ", threshold=50) is True

    def test_is_scanned_page_with_text(self) -> None:
        assert is_scanned_page("Hello world, this is a page with text.", threshold=20) is False

    def test_detect_no_text_layer_raises_when_all_scanned(self) -> None:
        document = PdfDocument(
            resource_id="res-1",
            total_pages=1,
            toc=[],
            pages=[PdfPage(page_number=1, text="", blocks=[])],
        )
        from app.core.exceptions import NoTextLayerError

        with pytest.raises(NoTextLayerError):
            detect_no_text_layer(document, threshold=20)

    def test_detect_no_text_layer_allows_some_text(self) -> None:
        document = PdfDocument(
            resource_id="res-1",
            total_pages=2,
            toc=[],
            pages=[
                PdfPage(page_number=1, text="", blocks=[]),
                PdfPage(page_number=2, text="Some text content here", blocks=[]),
            ],
        )
        detect_no_text_layer(document, threshold=20)

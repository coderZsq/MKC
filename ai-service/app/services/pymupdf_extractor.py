from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.exceptions import CorruptPdfError, EncryptedPdfError, NoTextLayerError
from app.models.pdf import PdfBlock, PdfDocument, PdfPage, PdfTocEntry

logger = logging.getLogger(__name__)


class PyMuPDFExtractor:
    """Extract structured text, blocks and TOC from a PDF using PyMuPDF."""

    def __init__(self, ocr_threshold: int = 50) -> None:
        self._ocr_threshold = ocr_threshold

    def extract(self, pdf_path: Path, resource_id: str = "") -> PdfDocument:
        """Open ``pdf_path`` and return a structured PDF document."""
        try:
            doc = self._open_document(pdf_path)
        except (EncryptedPdfError, CorruptPdfError):
            raise
        except Exception as exc:
            logger.exception("failed to open PDF: %s", pdf_path)
            raise CorruptPdfError(f"无法打开 PDF 文件: {exc}") from exc

        with doc:
            try:
                pages = self._extract_pages(doc)
                toc = self._extract_toc(doc)
            except Exception as exc:
                logger.exception("failed to extract text from PDF: %s", pdf_path)
                raise CorruptPdfError(f"PDF 文本提取失败: {exc}") from exc

        return PdfDocument(
            resource_id=resource_id,
            total_pages=len(pages),
            toc=toc,
            pages=pages,
        )

    def _open_document(self, pdf_path: Path) -> Any:
        """Open a PDF and reject encrypted documents."""
        try:
            import fitz
        except ImportError as exc:
            raise CorruptPdfError("PyMuPDF is not installed") from exc

        try:
            doc = fitz.open(str(pdf_path))
        except fitz.FileDataError as exc:
            raise CorruptPdfError("PDF 文件损坏") from exc
        except RuntimeError as exc:
            raise CorruptPdfError(f"无法打开 PDF 文件: {exc}") from exc

        if doc.is_encrypted:
            doc.close()
            raise EncryptedPdfError("无法解析加密 PDF")

        return doc

    def _extract_pages(self, doc: Any) -> list[PdfPage]:
        """Extract text and block coordinates from each page."""
        pages: list[PdfPage] = []
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text()
            blocks = page.get_text("blocks")
            page_blocks = [
                PdfBlock(
                    x=block[0],
                    y=block[1],
                    width=block[2] - block[0],
                    height=block[3] - block[1],
                    text=str(block[4]),
                )
                for block in blocks
            ]
            pages.append(
                PdfPage(
                    page_number=page_index + 1,
                    text=text,
                    blocks=page_blocks,
                )
            )
        return pages

    @staticmethod
    def _extract_toc(doc: Any) -> list[PdfTocEntry]:
        """Convert the document outline to a list of TOC entries."""
        toc: list[PdfTocEntry] = []
        for entry in doc.get_toc():
            # TOC entries are tuples of (level, title, page, ...).
            if len(entry) >= 3:
                toc.append(
                    PdfTocEntry(
                        level=int(entry[0]),
                        title=str(entry[1]),
                        page=int(entry[2]),
                    )
                )
        return toc


def is_scanned_page(page_text: str, threshold: int = 50) -> bool:
    """Return True when a page has fewer characters than ``threshold``."""
    return len(page_text.strip()) < threshold


def detect_no_text_layer(document: PdfDocument, threshold: int) -> None:
    """Raise ``NoTextLayerError`` if every page looks like a scanned image.

    A page is considered scanned when its stripped text length is below
    ``threshold``. If all pages are scanned, the PDF requires OCR.
    """
    if not document.pages:
        return

    scanned_pages = sum(1 for page in document.pages if is_scanned_page(page.text, threshold))
    if scanned_pages == len(document.pages):
        raise NoTextLayerError()

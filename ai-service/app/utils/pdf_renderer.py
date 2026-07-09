from __future__ import annotations

import logging
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from app.core.exceptions import CorruptPdfError

logger = logging.getLogger(__name__)


class RenderPage(NamedTuple):
    """A rendered PDF page with its position in the document."""

    page_number: int
    total_pages: int
    image_path: Path


class PdfRenderer:
    """Render PDF pages to raster images using PyMuPDF."""

    def __init__(self, dpi: int = 300) -> None:
        self._dpi = dpi

    def render_pages(self, pdf_path: Path) -> Iterator[RenderPage]:
        """Yield a ``RenderPage`` for each page of ``pdf_path``.

        The temporary directory holding the images is cleaned up once the
        iterator is exhausted or closed.
        """
        try:
            import fitz
        except ImportError as exc:
            raise CorruptPdfError("PyMuPDF is not installed") from exc

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            try:
                doc = fitz.open(str(pdf_path))
            except fitz.FileDataError as exc:
                raise CorruptPdfError("PDF 文件损坏") from exc
            except RuntimeError as exc:
                logger.exception("failed to open PDF with PyMuPDF: %s", pdf_path)
                raise CorruptPdfError("无法打开 PDF 文件") from exc

            with doc:
                scale = self._dpi / 72
                matrix = fitz.Matrix(scale, scale)
                total_pages = doc.page_count
                for page_index in range(total_pages):
                    page = doc.load_page(page_index)
                    pixmap = page.get_pixmap(matrix=matrix)
                    image_path = output_dir / f"page_{page_index:04d}.png"
                    pixmap.save(str(image_path))
                    yield RenderPage(
                        page_number=page_index + 1,
                        total_pages=total_pages,
                        image_path=image_path,
                    )

    @property
    def dpi(self) -> int:
        return self._dpi

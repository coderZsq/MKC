from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from app.core.exceptions import OcrNoTextError, OcrPageFailedError
from app.models.pdf import PdfBlock, PdfDocument, PdfPage
from app.utils.pdf_renderer import PdfRenderer, RenderPage

logger = logging.getLogger(__name__)


class _OcrEngine(Protocol):
    def recognize(self, image_path: Path) -> list[PdfBlock]: ...


class OcrService:
    """Orchestrate rendering and OCR for scanned PDFs."""

    def __init__(
        self,
        renderer: PdfRenderer,
        engine: _OcrEngine,
        max_pages_in_memory: int = 5,
    ) -> None:
        self._renderer = renderer
        self._engine = engine
        self._max_pages_in_memory = max(1, max_pages_in_memory)

    def process_pdf(
        self,
        pdf_path: Path,
        resource_id: str = "",
        progress_callback: Callable[[int], None] | None = None,
    ) -> PdfDocument:
        """Render ``pdf_path`` and run OCR, returning a structured document."""
        pages: list[PdfPage] = []
        render_iter = iter(self._renderer.render_pages(pdf_path))

        while True:
            batch = list(itertools.islice(render_iter, self._max_pages_in_memory))
            if not batch:
                break

            for render_page in batch:
                pages.append(self._build_page(render_page))
                if progress_callback is not None and render_page.total_pages > 0:
                    progress = int(
                        min(render_page.page_number / render_page.total_pages * 100, 100)
                    )
                    progress_callback(progress)

            for render_page in batch:
                render_page.image_path.unlink(missing_ok=True)

        if not pages or all(not page.text.strip() for page in pages):
            raise OcrNoTextError()

        return PdfDocument(
            resource_id=resource_id,
            total_pages=len(pages),
            toc=[],
            pages=pages,
        )

    def _build_page(self, render_page: RenderPage) -> PdfPage:
        """Run OCR on a single rendered page and return a ``PdfPage``."""
        blocks = sorted(
            self._recognize_page(render_page.image_path, render_page.page_number),
            key=lambda block: (block.y, block.x),
        )
        text = "\n".join(block.text for block in blocks)
        return PdfPage(
            page_number=render_page.page_number,
            text=text,
            blocks=blocks,
        )

    def _recognize_page(self, image_path: Path, page_number: int) -> list[PdfBlock]:
        """Run OCR on a single page, returning an empty list on page failure."""
        try:
            return list(self._engine.recognize(image_path))
        except OcrPageFailedError as exc:
            logger.warning(
                "OCR failed for page %s (%s); continuing with remaining pages",
                page_number,
                exc,
            )
            return []

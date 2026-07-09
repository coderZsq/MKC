from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import CorruptPdfError
from app.utils.pdf_renderer import PdfRenderer, RenderPage


def _make_text_pdf(output_path: Path) -> Path:
    """Create a PDF with two pages of text at ``output_path``."""
    import fitz

    doc = fitz.open()

    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((50, 100), "Hello World")

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((50, 100), "Page two")

    doc.save(str(output_path))
    doc.close()
    return output_path


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    return _make_text_pdf(tmp_path / "test.pdf")


class TestPdfRenderer:
    def test_render_pages_yields_one_image_per_page(self, text_pdf: Path) -> None:
        renderer = PdfRenderer(dpi=100)
        images: list[RenderPage] = []
        for render_page in renderer.render_pages(text_pdf):
            assert render_page.image_path.exists()
            assert render_page.image_path.stat().st_size > 0
            assert render_page.page_number == len(images) + 1
            assert render_page.total_pages == 2
            images.append(render_page)

        assert len(images) == 2

    def test_render_pages_produces_png_images(self, text_pdf: Path) -> None:
        renderer = PdfRenderer(dpi=100)
        images = list(renderer.render_pages(text_pdf))

        assert all(render_page.image_path.suffix == ".png" for render_page in images)

    def test_render_pages_cleans_up_temp_directory(self, text_pdf: Path) -> None:
        renderer = PdfRenderer(dpi=100)
        images = list(renderer.render_pages(text_pdf))

        assert images
        assert not images[0].image_path.parent.exists()

    def test_render_pages_raises_on_corrupt_pdf(self, tmp_path: Path) -> None:
        renderer = PdfRenderer(dpi=100)
        pdf_path = tmp_path / "corrupt.pdf"
        pdf_path.write_bytes(b"not a pdf")

        with pytest.raises(CorruptPdfError):
            list(renderer.render_pages(pdf_path))

    def test_dpi_property(self) -> None:
        renderer = PdfRenderer(dpi=200)
        assert renderer.dpi == 200

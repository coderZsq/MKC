from __future__ import annotations

import logging
from pathlib import Path

from app.core.exceptions import OcrPageFailedError, OcrUnavailableError
from app.models.pdf import PdfBlock

logger = logging.getLogger(__name__)


class PaddleOCREngine:
    """Thin wrapper around PaddleOCR for PDF page text recognition."""

    def __init__(
        self,
        lang: str = "ch",
        use_gpu: bool = False,
        show_log: bool = False,
    ) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OcrUnavailableError("PaddleOCR is not installed") from exc

        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=use_gpu,
            show_log=show_log,
        )

    def recognize(self, image_path: Path) -> list[PdfBlock]:
        """Run OCR on ``image_path`` and return a list of text blocks."""
        try:
            raw_result = self._ocr.ocr(str(image_path), cls=True)
        except Exception as exc:
            logger.exception("OCR engine failed to process %s", image_path)
            raise OcrPageFailedError(f"OCR 识别失败: {exc}") from exc

        if not raw_result or raw_result[0] is None:
            return []

        blocks: list[PdfBlock] = []
        for line in raw_result[0]:
            if not line or len(line) != 2:
                continue
            bbox, prediction = line
            if not isinstance(prediction, list | tuple) or len(prediction) != 2:
                continue
            text, score = prediction
            if not isinstance(text, str):
                continue

            x_coordinates = [point[0] for point in bbox]
            y_coordinates = [point[1] for point in bbox]
            x = float(min(x_coordinates))
            y = float(min(y_coordinates))
            width = float(max(x_coordinates) - x)
            height = float(max(y_coordinates) - y)

            blocks.append(
                PdfBlock(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    text=text,
                    confidence=float(score),
                )
            )

        return blocks

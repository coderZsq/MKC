from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import OcrPageFailedError, OcrUnavailableError
from app.models.pdf import PdfBlock
from app.services.paddle_ocr_engine import PaddleOCREngine


class _FakePaddleOCR:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def ocr(self, _image_path: str, **_kwargs: object) -> list:
        return [
            [
                [
                    [[10, 20], [110, 20], [110, 40], [10, 40]],
                    ("Hello", 0.95),
                ],
                [
                    [[10, 50], [150, 50], [150, 70], [10, 70]],
                    ("World", 0.88),
                ],
            ]
        ]


class _FailingPaddleOCR:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def ocr(self, _image_path: str, **_kwargs: object) -> None:
        raise RuntimeError("model crashed")


class TestPaddleOCREngine:
    def test_recognize_returns_blocks_with_confidence(self) -> None:
        fake_module = MagicMock()
        fake_module.PaddleOCR = _FakePaddleOCR
        with patch.dict(sys.modules, {"paddleocr": fake_module}):
            engine = PaddleOCREngine(lang="ch")

        blocks = engine.recognize(Path("/tmp/page.png"))

        assert len(blocks) == 2
        assert blocks[0].text == "Hello"
        assert blocks[0].x == 10
        assert blocks[0].y == 20
        assert blocks[0].width == 100
        assert blocks[0].height == 20
        assert blocks[0].confidence == pytest.approx(0.95)
        assert blocks[1].text == "World"
        assert blocks[1].confidence == pytest.approx(0.88)

    def test_recognize_returns_empty_list_when_no_text_found(self) -> None:
        class EmptyPaddleOCR:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def ocr(self, _image_path: str, **_kwargs: object) -> list:
                return [None]

        fake_module = MagicMock()
        fake_module.PaddleOCR = EmptyPaddleOCR
        with patch.dict(sys.modules, {"paddleocr": fake_module}):
            engine = PaddleOCREngine(lang="ch")

        blocks = engine.recognize(Path("/tmp/page.png"))

        assert blocks == []

    def test_recognize_raises_page_failed_on_engine_error(self) -> None:
        fake_module = MagicMock()
        fake_module.PaddleOCR = _FailingPaddleOCR
        with patch.dict(sys.modules, {"paddleocr": fake_module}):
            engine = PaddleOCREngine(lang="ch")

        with pytest.raises(OcrPageFailedError):
            engine.recognize(Path("/tmp/page.png"))

    def test_init_raises_unavailable_when_paddleocr_missing(self) -> None:
        with patch.dict(sys.modules, {"paddleocr": None}), pytest.raises(OcrUnavailableError):
            PaddleOCREngine(lang="ch")

    def test_recognize_skips_malformed_lines(self) -> None:
        class MalformedPaddleOCR:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def ocr(self, _image_path: str, **_kwargs: object) -> list:
                return [
                    [
                        None,
                        ([[0, 0], [10, 0], [10, 10], [0, 10]], ("ok", 0.99)),
                        [[0, 0], [10, 0], [10, 10], [0, 10]],
                        ([[0, 0], [10, 0], [10, 10], [0, 10]], ("bad",)),
                    ]
                ]

        fake_module = MagicMock()
        fake_module.PaddleOCR = MalformedPaddleOCR
        with patch.dict(sys.modules, {"paddleocr": fake_module}):
            engine = PaddleOCREngine(lang="ch")

        blocks = engine.recognize(Path("/tmp/page.png"))

        assert len(blocks) == 1
        assert blocks[0].text == "ok"
        assert isinstance(blocks[0], PdfBlock)

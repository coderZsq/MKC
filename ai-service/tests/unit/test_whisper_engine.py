from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.whisper_engine import WhisperEngine


@pytest.fixture
def engine() -> WhisperEngine:
    return WhisperEngine(
        model_name="tiny",
        device="cpu",
        compute_type="int8",
        model_dir="/tmp/whisper",
        beam_size=5,
        best_of=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        chunk_length=30,
    )


class FakeSegment:
    def __init__(
        self,
        start: float,
        end: float,
        text: str,
        avg_logprob: float,
    ) -> None:
        self.start = start
        self.end = end
        self.text = text
        self.avg_logprob = avg_logprob


@patch("app.services.whisper_engine.WhisperModel")
def test_load_creates_model(mock_model_class: MagicMock, engine: WhisperEngine) -> None:
    engine.load()

    mock_model_class.assert_called_once_with(
        "tiny",
        device="cpu",
        compute_type="int8",
        download_root="/tmp/whisper",
    )
    assert engine._model is mock_model_class.return_value


@patch("app.services.whisper_engine.WhisperModel")
def test_transcribe_yields_segments(mock_model_class: MagicMock, engine: WhisperEngine) -> None:
    fake_segments = [
        FakeSegment(0.0, 2.0, "你好", -0.5),
        FakeSegment(2.5, 4.5, "世界", -0.6),
    ]
    fake_info = MagicMock(language="zh", language_probability=0.95)
    mock_model = mock_model_class.return_value
    mock_model.transcribe.return_value = (iter(fake_segments), fake_info)

    engine.load()
    results = list(engine.transcribe(Path("/tmp/audio.wav"), language="zh"))

    assert len(results) == 2
    assert results[0] == {
        "start": 0.0,
        "end": 2.0,
        "text": "你好",
        "confidence": -0.5,
    }
    assert results[1] == {
        "start": 2.5,
        "end": 4.5,
        "text": "世界",
        "confidence": -0.6,
    }
    mock_model.transcribe.assert_called_once()
    call_kwargs = mock_model.transcribe.call_args.kwargs
    assert call_kwargs["language"] == "zh"
    assert call_kwargs["beam_size"] == 5
    assert call_kwargs["vad_filter"] is True


@patch("app.services.whisper_engine.WhisperModel")
def test_transcribe_auto_loads_model(mock_model_class: MagicMock, engine: WhisperEngine) -> None:
    fake_segments = [FakeSegment(0.0, 1.0, "test", -0.3)]
    fake_info = MagicMock()
    mock_model = mock_model_class.return_value
    mock_model.transcribe.return_value = (iter(fake_segments), fake_info)

    assert engine._model is None
    list(engine.transcribe(Path("/tmp/audio.wav")))

    assert engine._model is not None
    mock_model_class.assert_called_once()

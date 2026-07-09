from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AudioProcessingError
from app.services.audio_processor import AudioProcessor


@pytest.fixture
def processor() -> AudioProcessor:
    return AudioProcessor(sample_rate=16000)


@pytest.fixture
def sample_wav(tmp_path: Path) -> Path:
    """Create a 2-second mono 16kHz WAV file."""
    wav_path = tmp_path / "sample.wav"
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 2 * 16000 * 2)
    return wav_path


@patch("app.services.audio_processor.ffmpeg")
def test_convert_to_wav_success(
    mock_ffmpeg: MagicMock,
    processor: AudioProcessor,
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.mp3"
    target = tmp_path / "output.wav"
    source.write_text("fake audio")

    result = processor.convert_to_wav(source, target)

    assert result == target
    mock_ffmpeg.input.assert_called_once_with(str(source))
    output_call = mock_ffmpeg.input.return_value.output
    output_call.assert_called_once_with(
        str(target),
        ar=16000,
        ac=1,
        acodec="pcm_s16le",
    )
    output_call.return_value.run.assert_called_once_with(
        overwrite_output=True,
        quiet=True,
    )


@patch("app.services.audio_processor.ffmpeg")
def test_convert_to_wav_failure(
    mock_ffmpeg: MagicMock,
    processor: AudioProcessor,
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.mp3"
    target = tmp_path / "output.wav"
    source.write_text("fake audio")

    import ffmpeg

    mock_ffmpeg.Error = ffmpeg.Error
    mock_ffmpeg.input.return_value.output.return_value.run.side_effect = ffmpeg.Error(
        "failed",
        stderr=b"invalid audio",
        stdout=b"",
    )

    with pytest.raises(AudioProcessingError) as exc_info:
        processor.convert_to_wav(source, target)

    assert exc_info.value.code == "INVALID_AUDIO"
    assert "invalid audio" in exc_info.value.message


def test_get_duration(sample_wav: Path, processor: AudioProcessor) -> None:
    duration = processor.get_duration(sample_wav)
    assert duration == pytest.approx(2.0, rel=0.01)


def test_get_duration_unsupported_format(processor: AudioProcessor, tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("not audio")

    with pytest.raises(AudioProcessingError) as exc_info:
        processor.get_duration(bad_file)

    assert exc_info.value.code == "INVALID_AUDIO"

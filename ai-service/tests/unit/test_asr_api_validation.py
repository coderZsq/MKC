from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.api.asr import _validate_audio_url
from app.core.exceptions import AudioProcessingError


@patch("app.api.asr.AudioProcessor")
@patch("app.api.asr.download_audio")
def test_validate_audio_url_success(
    mock_download_audio: MagicMock,
    mock_processor_class: MagicMock,
) -> None:
    _validate_audio_url("minio://resources/audio.mp3")

    mock_download_audio.assert_called_once()
    called_args = mock_download_audio.call_args.args
    assert called_args[0] == "minio://resources/audio.mp3"
    assert isinstance(called_args[1], Path)
    mock_processor_class.return_value.convert_to_wav.assert_called_once()


@patch("app.api.asr.AudioProcessor")
@patch("app.api.asr.download_audio")
def test_validate_audio_url_failure(
    mock_download_audio: MagicMock,
    mock_processor_class: MagicMock,
) -> None:
    mock_processor_class.return_value.convert_to_wav.side_effect = AudioProcessingError(
        "cannot decode audio"
    )

    try:
        _validate_audio_url("minio://resources/corrupted.mp3")
    except AudioProcessingError as exc:
        assert exc.message == "cannot decode audio"
    else:
        raise AssertionError("expected AudioProcessingError")

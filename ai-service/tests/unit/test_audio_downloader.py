from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AudioProcessingError
from app.services.audio_downloader import download_audio


def _minio_settings(ai_config: dict) -> MagicMock:
    return MagicMock(
        ai_config=ai_config,
        minio_access_key="test-access-key",
        minio_secret_key="test-secret-key",
    )


@patch("app.services.audio_downloader._minio_client")
def test_download_minio_scheme_success(
    mock_minio_client: MagicMock,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.mp3"
    client = MagicMock()
    mock_minio_client.return_value = client

    with patch(
        "app.services.audio_downloader.settings",
        _minio_settings({"minio": {"bucket": "resources", "endpoint": "localhost:9000"}}),
    ):
        download_audio("minio://resources/audio.mp3", target)

    mock_minio_client.assert_called_once_with({"bucket": "resources", "endpoint": "localhost:9000"})
    client.fget_object.assert_called_once_with("resources", "audio.mp3", str(target))


@patch("app.services.audio_downloader._minio_client")
def test_download_minio_scheme_uses_config_bucket(
    mock_minio_client: MagicMock,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.mp3"
    client = MagicMock()
    mock_minio_client.return_value = client

    with patch(
        "app.services.audio_downloader.settings",
        _minio_settings({"minio": {"bucket": "resources"}}),
    ):
        download_audio("minio:///audio.mp3", target)

    client.fget_object.assert_called_once_with("resources", "audio.mp3", str(target))


@patch("app.services.audio_downloader._minio_client")
def test_download_minio_scheme_failure(
    mock_minio_client: MagicMock,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.mp3"
    client = MagicMock()
    client.fget_object.side_effect = Exception("access denied")
    mock_minio_client.return_value = client

    with (
        patch(
            "app.services.audio_downloader.settings",
            _minio_settings({"minio": {"bucket": "resources"}}),
        ),
        pytest.raises(AudioProcessingError) as exc_info,
    ):
        download_audio("minio://resources/audio.mp3", target)

    assert exc_info.value.code == "INVALID_AUDIO"
    assert "access denied" in exc_info.value.message


def test_download_unsupported_scheme(tmp_path: Path) -> None:
    target = tmp_path / "target.mp3"

    with pytest.raises(AudioProcessingError) as exc_info:
        download_audio("ftp://example.com/audio.mp3", target)

    assert exc_info.value.code == "INVALID_AUDIO"
    assert "unsupported" in exc_info.value.message


def test_download_minio_missing_credentials(tmp_path: Path) -> None:
    target = tmp_path / "target.mp3"

    with (
        patch(
            "app.services.audio_downloader.settings",
            MagicMock(
                ai_config={"minio": {"bucket": "resources"}},
                minio_access_key="",
                minio_secret_key="",
            ),
        ),
        pytest.raises(AudioProcessingError) as exc_info,
    ):
        download_audio("minio://resources/audio.mp3", target)

    assert exc_info.value.code == "INVALID_AUDIO"
    assert "credentials" in exc_info.value.message

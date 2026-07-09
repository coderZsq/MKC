from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import PdfNotFoundError, PdfParseError
from app.services.minio_storage import download_file, upload_json


class TestDownloadFile:
    @patch("app.services.minio_storage._minio_client")
    def test_download_file_success(self, mock_minio_client: MagicMock, tmp_path: Path) -> None:
        target = tmp_path / "source.pdf"
        download_file("minio://resources/doc.pdf", target)
        mock_minio_client.return_value.fget_object.assert_called_once_with(
            "resources", "doc.pdf", str(target)
        )

    def test_download_file_unsupported_scheme(self, tmp_path: Path) -> None:
        target = tmp_path / "source.pdf"
        with pytest.raises(PdfParseError, match="unsupported PDF URL scheme"):
            download_file("https://example.com/doc.pdf", target)

    def test_download_file_missing_object_name(self, tmp_path: Path) -> None:
        target = tmp_path / "source.pdf"
        with pytest.raises(PdfParseError, match="invalid minio URL"):
            download_file("minio://resources/", target)

    @patch("app.services.minio_storage._minio_client")
    def test_download_file_not_found(self, mock_minio_client: MagicMock, tmp_path: Path) -> None:
        target = tmp_path / "source.pdf"
        mock_minio_client.return_value.fget_object.side_effect = Exception("not found")
        with pytest.raises(PdfNotFoundError, match="failed to download PDF from minio"):
            download_file("minio://resources/doc.pdf", target)

    def test_download_file_path_traversal_normalized(self, tmp_path: Path) -> None:
        target = tmp_path / "source.pdf"
        with patch("app.services.minio_storage._minio_client") as mock_minio_client:
            download_file("minio://resources/../other/doc.pdf", target)
            args = mock_minio_client.return_value.fget_object.call_args
            assert args[0][1] == "other/doc.pdf"


class TestUploadJson:
    @patch("app.services.minio_storage._minio_client")
    def test_upload_json_success(self, mock_minio_client: MagicMock) -> None:
        url = upload_json({"pages": []}, "results/task-1/parsed.json")
        assert url == "minio://mkc-resources/results/task-1/parsed.json"
        mock_minio_client.return_value.put_object.assert_called_once()

    @patch("app.services.minio_storage._minio_client")
    def test_upload_json_failure(self, mock_minio_client: MagicMock) -> None:
        mock_minio_client.return_value.put_object.side_effect = Exception("upload failed")
        with pytest.raises(PdfParseError, match="failed to upload PDF result"):
            upload_json({"pages": []}, "results/task-1/parsed.json")

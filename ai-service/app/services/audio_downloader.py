from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.core.exceptions import AudioProcessingError


def _minio_client(minio_cfg: dict[str, Any]) -> Any:
    try:
        from minio import Minio
    except ImportError as exc:
        raise AudioProcessingError("minio SDK is not installed") from exc

    endpoint = minio_cfg.get("endpoint") or settings.minio_endpoint or "localhost:9000"
    use_ssl = minio_cfg.get("use_ssl", settings.minio_use_ssl)
    region = minio_cfg.get("region") or settings.minio_region
    access_key = settings.minio_access_key
    secret_key = settings.minio_secret_key

    if not access_key or not secret_key:
        raise AudioProcessingError("MinIO credentials are not configured")

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        secure=use_ssl,
    )


def download_audio(url: str, target: Path) -> None:
    """Download audio from a minio:// URL to the target path.

    Only the minio:// scheme is supported; arbitrary file:// and http(s)://
    schemes are rejected to prevent local file disclosure and SSRF.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme != "minio":
        raise AudioProcessingError(
            f"unsupported audio URL scheme: {scheme}. Only minio:// is supported."
        )

    minio_cfg = (settings.ai_config or {}).get("minio", {})
    bucket = parsed.netloc or minio_cfg.get("bucket") or settings.minio_bucket
    object_name = parsed.path.lstrip("/")

    if not bucket or not object_name:
        raise AudioProcessingError("invalid minio URL: missing bucket or object name")

    client = _minio_client(minio_cfg)
    try:
        client.fget_object(bucket, object_name, str(target))
    except Exception as exc:
        raise AudioProcessingError(f"failed to download audio from minio: {exc}") from exc

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.core.exceptions import PdfNotFoundError, PdfParseError

logger = logging.getLogger(__name__)


def _minio_client(minio_cfg: dict[str, Any]) -> Any:
    """Build a MinIO client from configuration and environment variables."""
    try:
        from minio import Minio
    except ImportError as exc:
        raise PdfParseError("minio SDK is not installed") from exc

    endpoint = minio_cfg.get("endpoint") or settings.minio_endpoint or "localhost:9000"
    use_ssl = minio_cfg.get("use_ssl", settings.minio_use_ssl)
    region = minio_cfg.get("region") or settings.minio_region
    access_key = settings.minio_access_key
    secret_key = settings.minio_secret_key

    if not access_key or not secret_key:
        raise PdfParseError("MinIO credentials are not configured")

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        secure=use_ssl,
    )


def download_file(url: str, target: Path) -> None:
    """Download a file from a ``minio://`` URL to ``target``.

    Only the ``minio://`` scheme is supported to prevent local file disclosure
    and SSRF via arbitrary ``file://`` or ``http(s)://`` URLs.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme != "minio":
        raise PdfParseError(f"unsupported PDF URL scheme: {scheme}. Only minio:// is supported.")

    minio_cfg = (settings.ai_config or {}).get("minio", {})
    bucket = parsed.netloc or minio_cfg.get("bucket") or settings.minio_bucket
    object_name = _normalize_object_name(parsed.path.lstrip("/"))

    if not bucket or not object_name:
        raise PdfParseError("invalid minio URL: missing bucket or object name")

    client = _minio_client(minio_cfg)
    try:
        client.fget_object(bucket, object_name, str(target))
    except Exception as exc:
        logger.warning("failed to download PDF from minio: %s", exc)
        raise PdfNotFoundError("failed to download PDF from minio") from exc


def _normalize_object_name(path: str) -> str:
    """Collapse path traversal segments and strip leading/trailing slashes."""
    parts = [part for part in path.split("/") if part and part != "."]
    cleaned: list[str] = []
    for part in parts:
        if part == "..":
            if cleaned:
                cleaned.pop()
            continue
        cleaned.append(part)
    return "/".join(cleaned)


def upload_json(data: dict[str, Any], key: str, content_type: str = "application/json") -> str:
    """Upload JSON data to MinIO under ``key`` and return a ``minio://`` URI.

    The Gateway is responsible for generating presigned download URLs; workers
    must store stable ``minio://bucket/object`` references so that bucket
    migrations and URL expiry do not invalidate task results.
    """
    minio_cfg = (settings.ai_config or {}).get("minio", {})
    bucket = minio_cfg.get("bucket") or settings.minio_bucket or "mkc-resources"
    client = _minio_client(minio_cfg)

    content = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    body = BytesIO(content)
    try:
        client.put_object(
            bucket,
            key,
            body,
            length=len(content),
            content_type=content_type,
        )
        return f"minio://{bucket}/{key}"
    except Exception as exc:
        logger.exception("failed to upload JSON result to minio: %s", key)
        raise PdfParseError(f"failed to upload PDF result to minio: {exc}") from exc

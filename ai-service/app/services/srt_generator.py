from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from app.core.config import settings
from app.core.exceptions import SubtitleGenerationError
from app.models.asr import AsrSegment
from app.services.segment_merger import SegmentMerger
from app.utils.timecode import format_timecode

logger = logging.getLogger(__name__)


SUPPORTED_FORMATS = {"srt", "vtt"}


def _build_minio_client(minio_cfg: dict[str, Any]) -> Any:
    """Build a MinIO client from configuration and environment variables."""
    try:
        from minio import Minio
    except ImportError as exc:
        raise SubtitleGenerationError(
            "STORAGE_ERROR",
            "minio SDK is not installed",
        ) from exc

    endpoint = minio_cfg.get("endpoint") or settings.minio_endpoint or "localhost:9000"
    use_ssl = minio_cfg.get("use_ssl", settings.minio_use_ssl)
    region = minio_cfg.get("region") or settings.minio_region
    access_key = settings.minio_access_key
    secret_key = settings.minio_secret_key

    if not access_key or not secret_key:
        raise SubtitleGenerationError(
            "STORAGE_ERROR",
            "MinIO credentials are not configured",
        )

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        secure=use_ssl,
    )


class SrtGenerator:
    """Generate SRT/WebVTT subtitles from ASR segments and upload them to MinIO."""

    def __init__(
        self,
        min_duration: float = 1.0,
        max_duration: float = 6.0,
        max_chars: int = 80,
        output_format: str = "srt",
        language: str | None = None,
        presigned_expiry: int = 3600,
    ) -> None:
        if output_format not in SUPPORTED_FORMATS:
            raise SubtitleGenerationError(
                "INVALID_OUTPUT_FORMAT",
                f"unsupported subtitle format: {output_format}",
            )
        self.output_format = output_format
        self.presigned_expiry = presigned_expiry
        self._merger = SegmentMerger(
            min_duration=min_duration,
            max_duration=max_duration,
            max_chars=max_chars,
            language=language,
        )

    def generate(self, segments: list[AsrSegment], language: str | None = None) -> str:
        """Generate subtitle content from ``segments``."""
        if not segments:
            raise SubtitleGenerationError("EMPTY_SEGMENTS", "无可用转录结果")

        merger = SegmentMerger(
            min_duration=self._merger.min_duration,
            max_duration=self._merger.max_duration,
            max_chars=self._merger.max_chars,
            language=language,
        )
        merged = merger.merge(segments)
        if not merged:
            raise SubtitleGenerationError("EMPTY_SEGMENTS", "无可用转录结果")

        if self.output_format == "vtt":
            return self._generate_vtt(merged)
        return self._generate_srt(merged)

    def save_to_minio(self, content: str, key: str) -> str:
        """Upload ``content`` to MinIO under ``key`` and return a ``minio://`` URI."""
        minio_cfg = (settings.ai_config or {}).get("minio", {})
        bucket = minio_cfg.get("bucket") or settings.minio_bucket or "mkc-resources"
        client = _build_minio_client(minio_cfg)

        data = BytesIO(content.encode("utf-8"))
        try:
            client.put_object(
                bucket,
                key,
                data,
                length=len(data.getvalue()),
                content_type="text/plain; charset=utf-8",
            )
            return f"minio://{bucket}/{key}"
        except SubtitleGenerationError:
            raise
        except Exception as exc:
            logger.exception("failed to upload subtitle to minio: %s", key)
            raise SubtitleGenerationError("STORAGE_ERROR", "字幕存储失败") from exc

    @staticmethod
    def _generate_srt(segments: list[AsrSegment]) -> str:
        """Generate an SRT-formatted string."""
        blocks: list[str] = []
        for index, segment in enumerate(segments, start=1):
            start = format_timecode(segment.start)
            end = format_timecode(segment.end)
            blocks.append(f"{index}\n{start} --> {end}\n{segment.text}\n")
        return "\n".join(blocks)

    @staticmethod
    def _generate_vtt(segments: list[AsrSegment]) -> str:
        """Generate a WebVTT-formatted string."""
        lines = ["WEBVTT", ""]
        for segment in segments:
            start = format_timecode(segment.start, separator=".")
            end = format_timecode(segment.end, separator=".")
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        return "\n".join(lines)

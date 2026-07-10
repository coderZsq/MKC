from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.exceptions import (
    AsrProcessingError,
    AudioProcessingError,
    SubtitleGenerationError,
)
from app.models.asr import AsrResult, AsrSegment, AsrTaskRequest
from app.services.minio_storage import upload_json

logger = logging.getLogger(__name__)


def _default_download(_url: str, _target: Path) -> None:
    raise AudioProcessingError("no download function configured")


def _default_subtitle_generator() -> Any:
    from app.core.config import settings
    from app.services.srt_generator import SrtGenerator

    srt_cfg = (settings.ai_config or {}).get("srt", {})
    return SrtGenerator(
        min_duration=srt_cfg.get("min_duration", 1.0),
        max_duration=srt_cfg.get("max_duration", 6.0),
        max_chars=srt_cfg.get("max_chars", 80),
        output_format=srt_cfg.get("output_format", "srt"),
        presigned_expiry=srt_cfg.get("presigned_expiry", 3600),
    )


def _default_text_cleaning_service() -> Any:
    from app.core.config import settings
    from app.services.text_cleaning.factory import build_text_cleaning_service

    cfg = (settings.ai_config or {}).get("text_cleaning", {})
    return build_text_cleaning_service(cfg)


class AsrService:
    """Orchestrates audio download, preprocessing, transcription and result reporting."""

    def __init__(
        self,
        engine: Any,
        processor: Any,
        reporter: Any,
        download_func: Callable[[str, Path], None] | None = None,
        progress_interval: float = 5.0,
        subtitle_generator: Any | None = None,
        text_cleaning_service: Any | None = None,
        report_status: bool = True,
    ) -> None:
        self.engine = engine
        self.processor = processor
        self.reporter = reporter
        self._download_func = download_func or _default_download
        self._progress_interval = progress_interval
        self._subtitle_generator = subtitle_generator or _default_subtitle_generator()
        self._text_cleaning_service = text_cleaning_service or _default_text_cleaning_service()
        self._report_status = report_status

    def process(self, task: AsrTaskRequest) -> AsrResult:
        """Download, convert, transcribe and report the result for a task."""
        raw_path = None
        wav_path = None
        try:
            if self._report_status:
                self.reporter.mark_status(task.task_id, "running")
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp = Path(tmp_dir)
                raw_path = tmp / "source"
                wav_path = tmp / "converted.wav"

                self._download_func(task.audio_url, raw_path)
                self.processor.convert_to_wav(raw_path, wav_path)
                duration = self.processor.get_duration(wav_path)

                segments = self._transcribe_with_progress(task, wav_path, duration)
                cleaned_segments = self._text_cleaning_service.clean(segments)

                transcript_key = f"results/{task.task_id}/transcript.json"
                transcript_url = upload_json(
                    {"segments": [segment.model_dump() for segment in cleaned_segments]},
                    transcript_key,
                )
                result = AsrResult(
                    task_id=task.task_id,
                    resource_id=task.resource_id,
                    segments=cleaned_segments,
                    text=self._join_text(cleaned_segments, task.language),
                    duration=duration,
                    transcript_url=transcript_url,
                    subtitle_url=self._generate_subtitle(task, cleaned_segments),
                )
                if self._report_status:
                    self.reporter.mark_status(
                        task.task_id,
                        "completed",
                        result=result.model_dump(),
                    )
                return result
        except AudioProcessingError as exc:
            logger.error("audio processing failed for task %s: %s", task.task_id, exc)
            self._mark_failed(task.task_id, str(exc))
            raise
        except SubtitleGenerationError as exc:
            logger.error("subtitle generation failed for task %s: %s", task.task_id, exc)
            self._mark_failed(task.task_id, str(exc))
            raise
        except AsrProcessingError as exc:
            logger.error("asr processing failed for task %s: %s", task.task_id, exc)
            self._mark_failed(task.task_id, str(exc))
            raise
        except Exception as exc:
            logger.exception("unexpected error during asr for task %s", task.task_id)
            self._mark_failed(task.task_id, str(exc))
            raise AsrProcessingError(str(exc)) from exc

    def _mark_failed(self, task_id: str, error_message: str) -> None:
        if self._report_status:
            self.reporter.mark_status(task_id, "failed", error_message=error_message)

    def _transcribe_with_progress(
        self,
        task: AsrTaskRequest,
        wav_path: Path,
        duration: float,
    ) -> list[AsrSegment]:
        segments: list[AsrSegment] = []
        last_reported = 0.0

        try:
            for raw in self.engine.transcribe(wav_path, language=task.language):
                segment = AsrSegment(
                    start=raw["start"],
                    end=raw["end"],
                    text=raw["text"],
                    confidence=raw.get("confidence"),
                )
                segments.append(segment)

                if duration > 0:
                    progress = int(min(segment.end / duration * 100, 100))
                    if progress - last_reported >= self._progress_interval or progress >= 100:
                        self.reporter.report_progress(task.task_id, progress, "running")
                        last_reported = progress
        except Exception as exc:
            raise AsrProcessingError(f"transcription failed: {exc}") from exc

        return segments

    @staticmethod
    def _join_text(segments: list[AsrSegment], language: str | None) -> str:
        """Join segment text using language-appropriate spacing."""
        if language in {"zh", "zh-cn", "zh-tw", "ja", "ko"}:
            return "".join(segment.text for segment in segments)
        return " ".join(segment.text for segment in segments)

    def _generate_subtitle(
        self,
        task: AsrTaskRequest,
        segments: list[AsrSegment],
    ) -> str | None:
        """Generate a subtitle file from ``segments`` and upload it to MinIO."""
        if self._subtitle_generator is None:
            return None

        srt_content = self._subtitle_generator.generate(segments, language=task.language)
        key = f"results/{task.task_id}/subtitle.{self._subtitle_generator.output_format}"
        return str(self._subtitle_generator.save_to_minio(srt_content, key))

from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.exceptions import AsrProcessingError, AudioProcessingError
from app.models.asr import AsrResult, AsrSegment, AsrTaskRequest

logger = logging.getLogger(__name__)


def _default_download(_url: str, _target: Path) -> None:
    raise AudioProcessingError("no download function configured")


class AsrService:
    """Orchestrates audio download, preprocessing, transcription and result reporting."""

    def __init__(
        self,
        engine: Any,
        processor: Any,
        reporter: Any,
        download_func: Callable[[str, Path], None] | None = None,
        progress_interval: float = 5.0,
    ) -> None:
        self.engine = engine
        self.processor = processor
        self.reporter = reporter
        self._download_func = download_func or _default_download
        self._progress_interval = progress_interval

    def process(self, task: AsrTaskRequest) -> AsrResult:
        """Download, convert, transcribe and report the result for a task."""
        raw_path = None
        wav_path = None
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp = Path(tmp_dir)
                raw_path = tmp / "source"
                wav_path = tmp / "converted.wav"

                self._download_func(task.audio_url, raw_path)
                self.processor.convert_to_wav(raw_path, wav_path)
                duration = self.processor.get_duration(wav_path)

                self.reporter.mark_status(task.task_id, "running")
                segments = self._transcribe_with_progress(task, wav_path, duration)

                result = AsrResult(
                    task_id=task.task_id,
                    resource_id=task.resource_id,
                    segments=segments,
                    text=self._join_text(segments, task.language),
                    duration=duration,
                )
                self.reporter.mark_status(
                    task.task_id,
                    "completed",
                    result=result.model_dump(),
                )
                return result
        except AudioProcessingError as exc:
            logger.error("audio processing failed for task %s: %s", task.task_id, exc)
            self.reporter.mark_status(task.task_id, "failed", error_message=exc.message)
            raise
        except AsrProcessingError as exc:
            logger.error("asr processing failed for task %s: %s", task.task_id, exc)
            self.reporter.mark_status(task.task_id, "failed", error_message=exc.message)
            raise
        except Exception as exc:
            logger.exception("unexpected error during asr for task %s", task.task_id)
            self.reporter.mark_status(task.task_id, "failed", error_message=str(exc))
            raise AsrProcessingError(str(exc)) from exc

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

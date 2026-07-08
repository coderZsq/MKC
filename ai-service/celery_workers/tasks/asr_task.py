from __future__ import annotations

from typing import Any

from celery import Task

from app.core.config import settings
from app.core.exceptions import ModelLoadError
from app.models.asr import AsrTaskRequest
from app.services.asr_service import AsrService
from app.services.audio_downloader import download_audio
from app.services.audio_processor import AudioProcessor
from app.services.gateway_reporter import GatewayProgressReporter
from app.services.whisper_engine import WhisperEngine
from celery_workers.celery_app import celery_app


def _build_engine(model_name: str | None) -> WhisperEngine:
    asr_cfg = (settings.ai_config or {}).get("asr", {})
    effective_model = model_name or asr_cfg.get("default_model", "small")
    return WhisperEngine(
        model_name=effective_model,
        device=asr_cfg.get("device", "auto"),
        compute_type=asr_cfg.get("compute_type", "int8"),
        model_dir=asr_cfg.get("model_dir", "/models/whisper"),
        beam_size=asr_cfg.get("beam_size", 5),
        best_of=asr_cfg.get("best_of", 5),
        vad_filter=asr_cfg.get("vad_filter", True),
        vad_parameters=asr_cfg.get("vad_parameters", {}),
        chunk_length=asr_cfg.get("chunk_length", 30),
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def run_asr(self: Task, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Celery task that runs ASR for a queued audio file."""
    task = AsrTaskRequest.model_validate(payload)
    asr_cfg = (settings.ai_config or {}).get("asr", {})

    engine = _build_engine(task.model)
    processor = AudioProcessor(sample_rate=asr_cfg.get("sample_rate", 16000))
    reporter = GatewayProgressReporter()
    service = AsrService(
        engine=engine,
        processor=processor,
        reporter=reporter,
        download_func=download_audio,
        progress_interval=asr_cfg.get("progress_interval", 5.0),
    )

    try:
        result = service.process(task)
    except ModelLoadError as exc:
        fallback_model = asr_cfg.get("fallback_model")
        if (
            fallback_model
            and task.model != fallback_model
            and self.request.retries < self.max_retries
        ):
            task.model = fallback_model
            raise self.retry(  # noqa: B904
                exc=exc,
                args=[task_id, task.model_dump()],
            )
        reporter.mark_status(
            task_id,
            "failed",
            error_message=exc.message,
        )
        raise

    return result.model_dump()

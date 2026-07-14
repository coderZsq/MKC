from __future__ import annotations

import logging
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
from celery_workers.tasks.base import BaseAITask
from celery_workers.tasks.index_vectors_task import index_resource_vectors

logger = logging.getLogger(__name__)


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


@celery_app.task(bind=True, base=BaseAITask, autoretry_for=())
def run_asr(self: Task, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Celery task that runs ASR for a queued audio file.

    Automatic retry and exponential backoff are handled by :class:`BaseAITask`.
    When a requested model fails to load, the fallback model is used on retry
    attempts.
    """
    task = AsrTaskRequest.model_validate(payload)
    asr_cfg = (settings.ai_config or {}).get("asr", {})

    fallback_model = asr_cfg.get("fallback_model")
    if self.request.retries > 0 and fallback_model and task.model != fallback_model:
        task.model = fallback_model

    reporter = GatewayProgressReporter()
    reporter.mark_status(task_id, "running", attempt_count=self._attempt_count())

    try:
        engine = _build_engine(task.model)
        processor = AudioProcessor(sample_rate=asr_cfg.get("sample_rate", 16000))
        service = AsrService(
            engine=engine,
            processor=processor,
            reporter=reporter,
            download_func=download_audio,
            progress_interval=asr_cfg.get("progress_interval", 5.0),
            report_status=False,
        )
        result = service.process(task)
    except ModelLoadError as exc:
        if self.request.retries < self.request.max_retries:
            fallback_model = asr_cfg.get("fallback_model")
            if fallback_model:
                task.model = fallback_model
            retry_payload = task.model_dump()
            raise self.retry(args=[task_id, retry_payload]) from exc
        reporter.mark_status(
            task_id,
            "failed",
            error_message=str(exc),
            attempt_count=self._attempt_count(),
        )
        self._failure_reported = True
        raise

    result_dict = result.model_dump()

    try:
        index_resource_vectors.delay(
            task_id=task_id,
            user_id=task.user_id,
            resource_id=task.resource_id,
            source_type="audio",
            parsed_result=result_dict,
        )
    except Exception:
        logger.exception("Failed to enqueue vector indexing for resource %s", task.resource_id)

    return result_dict

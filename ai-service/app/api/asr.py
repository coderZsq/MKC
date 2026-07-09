from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Blueprint, request

from app.api.dependencies import check_internal_key
from app.core.config import settings
from app.core.exceptions import AudioProcessingError, ValidationException
from app.core.response import make_response
from app.models.asr import AsrTaskRequest
from app.services.audio_downloader import download_audio
from app.services.audio_processor import AudioProcessor
from celery_workers.tasks.asr_task import run_asr

asr_bp = Blueprint("asr", __name__)
asr_bp.before_request(check_internal_key)


def _validate_audio_url(audio_url: str) -> None:
    """Download and convert the referenced audio to verify it is usable.

    Raises AudioProcessingError when the audio cannot be downloaded or is not
    a valid audio format. The converted file is discarded; transcription is
    still performed asynchronously by the worker.
    """
    asr_cfg = (settings.ai_config or {}).get("asr", {})
    sample_rate = asr_cfg.get("sample_rate", 16000)
    processor = AudioProcessor(sample_rate=sample_rate)

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_path = Path(tmp_dir) / "source"
        wav_path = Path(tmp_dir) / "converted.wav"
        download_audio(audio_url, raw_path)
        processor.convert_to_wav(raw_path, wav_path)


@asr_bp.post("/asr")
def create_asr_task() -> tuple:
    """Queue an asynchronous ASR task."""
    data = request.get_json(silent=True) or {}
    try:
        task_request = AsrTaskRequest.model_validate(data)
    except Exception as exc:
        raise ValidationException(str(exc)) from exc

    try:
        _validate_audio_url(task_request.audio_url)
    except AudioProcessingError as exc:
        return make_response(
            success=False,
            error={"code": "INVALID_AUDIO", "message": exc.message},
            status=400,
        )

    payload = task_request.model_dump()
    run_asr.delay(task_id=task_request.task_id, payload=payload)

    return make_response(
        data={
            "task_id": task_request.task_id,
            "status": "pending",
            "message": "ASR task queued",
        },
        status=202,
    )

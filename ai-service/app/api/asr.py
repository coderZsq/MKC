from __future__ import annotations

from flask import Blueprint, request

from app.api.dependencies import check_internal_key
from app.core.exceptions import ValidationException
from app.core.response import make_response
from app.models.asr import AsrTaskRequest
from celery_workers.tasks.asr_task import run_asr

asr_bp = Blueprint("asr", __name__)
asr_bp.before_request(check_internal_key)


@asr_bp.post("/asr")
def create_asr_task() -> tuple:
    """Queue an asynchronous ASR task."""
    data = request.get_json(silent=True) or {}
    try:
        task_request = AsrTaskRequest.model_validate(data)
    except Exception as exc:
        raise ValidationException(str(exc)) from exc

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

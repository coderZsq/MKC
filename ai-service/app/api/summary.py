from __future__ import annotations

from flask import Blueprint, current_app, request

from app.api.dependencies import check_internal_key
from app.core.exceptions import ValidationException
from app.core.response import make_response
from app.models.summary import SummarizeRequest
from celery_workers.tasks.summarize_task import run_summarize

summary_bp = Blueprint("summary", __name__)
summary_bp.before_request(check_internal_key)


@summary_bp.post("/resources/<resource_id>/summarize")
def summarize_resource(resource_id: str) -> tuple:
    data = request.get_json(silent=True) or {}
    try:
        payload = SummarizeRequest.model_validate(data)
    except Exception as exc:
        raise ValidationException(str(exc)) from exc

    task_id = payload.task_id or f"sum-{resource_id}"
    if current_app.config.get("TESTING"):
        current_app.extensions["summary_service"].generate(resource_id, payload)
    else:
        run_summarize.delay(task_id=task_id, resource_id=resource_id, payload=payload.model_dump())

    return make_response(data={"task_id": task_id, "status": "pending"}, status=202)

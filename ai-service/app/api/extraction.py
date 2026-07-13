from __future__ import annotations

from flask import Blueprint, current_app, request

from app.api.dependencies import check_internal_key
from app.core.exceptions import ValidationException
from app.core.response import make_response
from app.models.extraction import ExtractTagsRequest
from celery_workers.tasks.extract_tags_task import run_extract_tags

extraction_bp = Blueprint("extraction", __name__)
extraction_bp.before_request(check_internal_key)


@extraction_bp.post("/resources/<resource_id>/extract-tags")
def extract_tags(resource_id: str) -> tuple:
    data = request.get_json(silent=True) or {}
    try:
        payload = ExtractTagsRequest.model_validate(data)
    except Exception as exc:
        raise ValidationException(str(exc)) from exc

    task_id = payload.task_id or f"tag-{resource_id}"
    if current_app.config.get("TESTING"):
        current_app.extensions["extraction_service"].extract(resource_id, payload)
    else:
        run_extract_tags.delay(
            task_id=task_id, resource_id=resource_id, payload=payload.model_dump()
        )

    return make_response(data={"task_id": task_id, "status": "pending"}, status=202)

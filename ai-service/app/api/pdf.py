from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, Response, request

from app.api.dependencies import check_internal_key
from app.core.exceptions import ValidationException
from app.core.response import make_response
from app.models.pdf import PdfParseResponse, PdfParseTask
from celery_workers.tasks.pdf_parse_task import run_pdf_parse

pdf_bp = Blueprint("pdf", __name__)
pdf_bp.before_request(check_internal_key)


def _validate_pdf_url(pdf_url: str) -> None:
    """Validate that ``pdf_url`` uses the allowed minio:// scheme."""
    parsed = urlparse(pdf_url)
    if parsed.scheme.lower() != "minio":
        raise ValidationException(
            f"unsupported PDF URL scheme: {parsed.scheme}. Only minio:// is supported."
        )
    if not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValidationException("invalid PDF URL: missing bucket or object name")


@pdf_bp.post("/pdf/parse")
def create_pdf_parse_task() -> tuple[Response, int]:
    """Queue an asynchronous PDF text-extraction task."""
    data = request.get_json(silent=True) or {}
    try:
        task_request = PdfParseTask.model_validate(data)
    except Exception as exc:
        raise ValidationException("invalid PDF parse request body") from exc

    _validate_pdf_url(task_request.pdf_url)

    payload = task_request.model_dump()
    run_pdf_parse.delay(task_id=task_request.task_id, payload=payload)

    response = PdfParseResponse(
        task_id=task_request.task_id,
        status="pending",
    )
    return make_response(
        data=response.model_dump(),
        status=202,
    )

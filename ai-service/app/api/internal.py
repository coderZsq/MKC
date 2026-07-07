from flask import Blueprint

from app.api.dependencies import check_internal_key
from app.core.response import make_response

internal_bp = Blueprint("internal", __name__)
internal_bp.before_request(check_internal_key)


@internal_bp.get("/health")
def internal_health() -> tuple:
    return make_response(data={"status": "ok", "service": "ai-service"}, status=200)

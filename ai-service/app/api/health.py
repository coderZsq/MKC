from typing import Any

from flask import Blueprint

from app.core.response import make_response
from app.extensions import redis_client
from celery_workers.celery_app import celery_app

health_bp = Blueprint("health", __name__)


def _ping_redis() -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False


def _ping_broker() -> bool:
    try:
        result = celery_app.control.ping(timeout=1.0)
        return bool(result)
    except Exception:
        return False


@health_bp.get("/health")
def health() -> tuple:
    redis_ok = _ping_redis()
    broker_ok = _ping_broker()

    data: dict[str, Any] = {
        "status": "ok",
        "service": "ai-service",
        "dependencies": {
            "redis": "ok" if redis_ok else "down",
            "celery_broker": "ok" if broker_ok else "down",
        },
    }
    return make_response(data=data, status=200)

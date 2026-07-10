from flask import Flask, Response

from app.api.asr import asr_bp
from app.api.chunking import chunking_bp
from app.api.embedding import embedding_bp
from app.api.health import health_bp
from app.api.internal import internal_bp
from app.api.pdf import pdf_bp
from app.api.vectors import vectors_bp
from app.core.config import settings
from app.core.exceptions import APIException
from app.core.response import make_response
from app.middleware.logging import init_request_logging
from app.middleware.request_id import init_request_id
from app.services.embedding.factory import (
    build_embedding_service,
    validate_embedding_config,
)
from app.services.embedding.service import EmbeddingService
from app.vector_store.factory import build_vector_store
from app.vector_store.vector_store import VectorStore
from celery_workers.celery_app import celery_app


def create_app(
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_object(settings)

    init_extensions(
        app,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    init_request_id(app)
    init_request_logging(app)
    register_blueprints(app)
    register_error_handlers(app)

    return app


def init_extensions(
    app: Flask,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
) -> None:
    if embedding_service is not None:
        app.extensions["embedding"] = embedding_service
    else:
        validate_embedding_config()
        app.extensions["embedding"] = build_embedding_service()

    if vector_store is not None:
        app.extensions["vector_store"] = vector_store
    else:
        app.extensions["vector_store"] = build_vector_store()
    celery_app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        timezone="Asia/Shanghai",
        enable_utc=True,
    )


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(internal_bp, url_prefix="/api/v1/internal")
    app.register_blueprint(asr_bp, url_prefix="/ai/v1")
    app.register_blueprint(pdf_bp, url_prefix="/ai/v1")
    app.register_blueprint(chunking_bp, url_prefix="/ai/v1")
    app.register_blueprint(embedding_bp, url_prefix="/ai/v1")
    app.register_blueprint(vectors_bp, url_prefix="/ai/v1")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIException)
    def handle_api_exception(error: APIException) -> tuple[Response, int]:
        return make_response(
            success=False,
            error={"code": error.code, "message": error.message},
            status=error.status_code,
        )

    @app.errorhandler(404)
    def handle_not_found(_: Exception) -> tuple[Response, int]:
        return make_response(
            success=False,
            error={"code": "NOT_FOUND", "message": "资源不存在"},
            status=404,
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(_: Exception) -> tuple[Response, int]:
        return make_response(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
            status=500,
        )

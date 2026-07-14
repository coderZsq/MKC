from __future__ import annotations

import logging
from typing import Any

from celery import Task

from app.services.chunking.factory import build_chunking_service
from app.services.embedding.factory import build_embedding_service
from app.services.vector_indexing import VectorIndexService, build_vector_indexing_config
from app.vector_store.factory import build_vector_store
from celery_workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    default_retry_delay=30,
    track_started=True,
    name="celery_workers.tasks.index_vectors_task.index_resource_vectors",
)
def index_resource_vectors(
    self: Task,
    task_id: str,
    user_id: str,
    resource_id: str,
    source_type: str,
    parsed_result: dict[str, Any],
) -> dict[str, Any]:
    """Embed and upsert a parsed PDF or ASR result into the vector store.

    This task is intentionally *not* based on :class:`BaseAITask` because it is
    an internal follow-up step; it must not report its own status to the Gateway
    as if it were the original business task.
    """
    config = build_vector_indexing_config()
    if not config.enabled:
        logger.info("Vector indexing is disabled; skipping resource %s", resource_id)
        return {"resource_id": resource_id, "upserted_count": 0}

    chunking_service = build_chunking_service()
    embedding_service = build_embedding_service()
    vector_store = build_vector_store()
    service = VectorIndexService(
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        vector_store=vector_store,
        strategy=config.strategy,
    )

    try:
        if source_type == "pdf":
            count = service.index_pdf(user_id, resource_id, parsed_result)
        elif source_type == "audio":
            count = service.index_asr(user_id, resource_id, parsed_result)
        else:
            raise ValueError(f"Unsupported source type for indexing: {source_type}")
    except Exception:
        logger.exception("Failed to index vectors for resource %s", resource_id)
        raise

    logger.info("Indexed %d vectors for resource %s", count, resource_id)
    return {"resource_id": resource_id, "upserted_count": count}

from __future__ import annotations

from typing import Any

from celery import Task

from app.core.config import settings
from app.models.extraction import ExtractTagsRequest
from app.services.extraction import (
    EntityResolver,
    ExtractionRepository,
    ExtractionService,
    LLMExtractionProvider,
    RuleExtractionProvider,
    TagNormalizer,
)
from app.services.llm import build_llm_client
from celery_workers.celery_app import celery_app
from celery_workers.tasks.base import BaseAITask


def build_extraction_service() -> ExtractionService:
    extraction_cfg = (settings.ai_config or {}).get("extraction", {})
    return ExtractionService(
        llm_provider=LLMExtractionProvider(build_llm_client(), extraction_cfg),
        rule_provider=RuleExtractionProvider(),
        tag_normalizer=TagNormalizer(extraction_cfg.get("tags", {})),
        entity_resolver=EntityResolver(),
        repository=ExtractionRepository(),
        config=extraction_cfg,
    )


@celery_app.task(bind=True, base=BaseAITask, autoretry_for=())
def run_extract_tags(
    self: Task, task_id: str, resource_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        result = build_extraction_service().extract(
            resource_id, ExtractTagsRequest.model_validate(payload)
        )
    except Exception as exc:
        if self.request.retries < self.request.max_retries:
            raise self.retry(
                kwargs={"task_id": task_id, "resource_id": resource_id, "payload": payload}
            ) from exc
        raise
    return result.model_dump(mode="json")

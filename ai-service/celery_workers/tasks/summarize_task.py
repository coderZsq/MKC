from __future__ import annotations

from typing import Any

from celery import Task

from app.core.config import settings
from app.models.summary import SummarizeRequest
from app.services.gateway_reporter import GatewayProgressReporter
from app.services.llm import build_llm_client
from app.services.summary import (
    MapReduceSummarizer,
    SectionSplitter,
    SummaryLLMProvider,
    SummaryRepository,
    SummaryService,
)
from celery_workers.celery_app import celery_app
from celery_workers.tasks.base import BaseAITask


def build_summary_service() -> SummaryService:
    summary_cfg = (settings.ai_config or {}).get("summary", {})
    llm_provider = SummaryLLMProvider(build_llm_client(), summary_cfg)
    return SummaryService(
        llm_provider=llm_provider,
        summarizer=MapReduceSummarizer(llm_provider, summary_cfg),
        splitter=SectionSplitter(),
        repository=SummaryRepository(),
        config=summary_cfg,
    )


@celery_app.task(bind=True, base=BaseAITask, autoretry_for=())
def run_summarize(
    self: Task, task_id: str, resource_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    reporter = GatewayProgressReporter()
    reporter.mark_status(task_id, "running", attempt_count=self._attempt_count())
    try:
        result = build_summary_service().generate(
            resource_id, SummarizeRequest.model_validate(payload)
        )
    except Exception as exc:
        if self.request.retries < self.request.max_retries:
            raise self.retry(
                kwargs={"task_id": task_id, "resource_id": resource_id, "payload": payload}
            ) from exc
        reporter.mark_status(
            task_id,
            "failed",
            error_message=str(exc),
            attempt_count=self._attempt_count(),
        )
        self._failure_reported = True
        raise
    return result.model_dump(mode="json")

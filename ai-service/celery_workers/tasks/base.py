from __future__ import annotations

from typing import Any

from celery import Task

from app.services.gateway_reporter import GatewayProgressReporter


class BaseAITask(Task):
    """Base Celery task that reports status to the Gateway and retries with backoff."""

    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 3600
    retry_jitter = True
    default_retry_delay = 60
    track_started = True

    def _attempt_count(self) -> int:
        return getattr(self.request, "retries", 0) + 1

    def _reporter(self) -> GatewayProgressReporter:
        return GatewayProgressReporter()

    def on_success(self, retval: Any, task_id: str, args: Any, kwargs: Any) -> None:
        if isinstance(retval, dict):
            self._reporter().mark_status(
                task_id,
                "completed",
                result=retval,
                attempt_count=self._attempt_count(),
            )
        else:
            self._reporter().mark_status(
                task_id,
                "completed",
                attempt_count=self._attempt_count(),
            )

    def on_retry(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        self._failure_reported = False
        self._reporter().mark_status(
            task_id,
            "running",
            attempt_count=self._attempt_count(),
        )

    def on_failure(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        if getattr(self, "_failure_reported", False):
            return
        self._reporter().mark_status(
            task_id,
            "failed",
            error_message=str(exc),
            attempt_count=self._attempt_count(),
        )


# Module-level helper for backward compatibility and explicit calls.
def report_status(
    task_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
    attempt_count: int | None = None,
) -> None:
    GatewayProgressReporter().mark_status(
        task_id,
        status,
        result=result,
        error_message=error_message,
        attempt_count=attempt_count,
    )

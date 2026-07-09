from __future__ import annotations

import logging
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class GatewayProgressReporter:
    """Reports ASR task progress and status to the Gateway internal API."""

    def __init__(
        self,
        base_url: str | None = None,
        internal_key: str | None = None,
        progress_path: str = "/api/v1/internal/tasks/{task_id}/progress",
        status_path: str = "/api/v1/internal/tasks/{task_id}/status",
        timeout: float = 5.0,
    ) -> None:
        gateway_cfg = (settings.ai_config or {}).get("gateway", {})
        self._base_url = base_url or gateway_cfg.get("base_url", "")
        self._internal_key = internal_key or settings.internal_api_key
        self._progress_path = progress_path
        self._status_path = status_path
        self._timeout = timeout

    def report_progress(self, task_id: str, progress: int, status: str) -> None:
        """Send a progress update to the Gateway."""
        url = self._build_url(self._progress_path, task_id)
        payload = {"progress": progress, "status": status}
        self._post(url, payload)

    def mark_status(
        self,
        task_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        attempt_count: int | None = None,
    ) -> None:
        """Send a status transition to the Gateway."""
        url = self._build_url(self._status_path, task_id)
        payload: dict[str, Any] = {
            "status": status,
            "result": result,
            "error_message": error_message,
        }
        if attempt_count is not None:
            payload["attempt_count"] = attempt_count
        self._post(url, payload)

    def _build_url(self, path_template: str, task_id: str) -> str:
        path = path_template.format(task_id=task_id)
        base_url = self._base_url.rstrip("/")
        return f"{base_url}{path}"

    def _post(self, url: str, payload: dict[str, Any]) -> None:
        if not self._base_url:
            logger.warning("gateway base_url is not configured, skipping progress report")
            return
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"X-Internal-Key": self._internal_key},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("failed to report progress to gateway: %s", exc)

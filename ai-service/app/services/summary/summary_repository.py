from __future__ import annotations

import logging
from typing import Any

import requests

from app.core.config import settings
from app.models.summary import SummaryResult
from app.services.minio_storage import upload_json

logger = logging.getLogger(__name__)


class SummaryRepository:
    def __init__(
        self,
        base_url: str | None = None,
        internal_key: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        gateway_cfg = (settings.ai_config or {}).get("gateway", {})
        self._base_url = (base_url or gateway_cfg.get("base_url", "")).rstrip("/")
        self._internal_key = internal_key or settings.internal_api_key
        self._timeout = timeout

    def save(self, result: SummaryResult) -> str | None:
        uri = upload_json(result.model_dump(mode="json"), f"{result.resource_id}/summary.json")
        if not self._base_url:
            logger.warning("gateway base_url is not configured, skipping summary persistence")
            return uri

        url = f"{self._base_url}/api/v1/internal/resources/{result.resource_id}/summaries"
        payload: dict[str, Any] = result.model_dump(mode="json", exclude={"created_at"})
        response = requests.post(
            url,
            json=payload,
            headers={"X-Internal-Key": self._internal_key},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return uri

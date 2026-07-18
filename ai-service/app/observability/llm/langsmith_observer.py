from __future__ import annotations

import os
from typing import Any

from app.observability.llm.observer import (
    LLMGenerationEvent,
    LLMObserverConfig,
    sanitize_event,
)


class LangSmithObserver:
    def __init__(self, config: LLMObserverConfig, client: Any | None = None) -> None:
        self._config = config
        if client is not None:
            self._client = client
            return
        from langsmith import Client

        self._client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))

    def record_generation(self, event: LLMGenerationEvent) -> None:
        event = sanitize_event(event, self._config)
        self._client.create_run(
            name="llm.complete",
            run_type="llm",
            project_name=os.getenv("LANGCHAIN_PROJECT") or None,
            inputs={"prompt": event.prompt},
            outputs={"completion": event.completion},
            extra={
                "metadata": {
                    "trace_id": event.trace_id,
                    "prompt_version": event.prompt_version,
                    "provider": event.provider,
                    "model": event.model,
                    "latency_ms": event.latency_ms,
                    "input_tokens": event.input_tokens,
                    "output_tokens": event.output_tokens,
                    "total_tokens": event.total_tokens,
                    "status": event.status,
                    "error_code": event.error_code,
                }
            },
        )

    def record_error(self, event: LLMGenerationEvent) -> None:
        self.record_generation(event)

    def flush(self) -> None:
        return None

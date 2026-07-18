from __future__ import annotations

import os
from typing import Any

from app.observability.llm.observer import (
    LLMGenerationEvent,
    LLMObserverConfig,
    sanitize_event,
)


class LangfuseObserver:
    def __init__(self, config: LLMObserverConfig, client: Any | None = None) -> None:
        self._config = config
        if client is not None:
            self._client = client
            return
        from langfuse import Langfuse

        self._client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST") or None,
        )

    def record_generation(self, event: LLMGenerationEvent) -> None:
        event = sanitize_event(event, self._config)
        trace = self._client.trace(
            id=event.trace_id or None,
            metadata={
                "prompt_version": event.prompt_version,
                "provider": event.provider,
                "status": event.status,
            },
        )
        trace.generation(
            name="llm.complete",
            model=event.model,
            input=event.prompt,
            output=event.completion,
            usage={
                "input": event.input_tokens,
                "output": event.output_tokens,
                "total": event.total_tokens,
            },
            metadata={
                "latency_ms": event.latency_ms,
                "trace_id": event.trace_id,
                "error_code": event.error_code,
            },
        )

    def record_error(self, event: LLMGenerationEvent) -> None:
        self.record_generation(event)

    def flush(self) -> None:
        flush = getattr(self._client, "flush", None)
        if callable(flush):
            flush()

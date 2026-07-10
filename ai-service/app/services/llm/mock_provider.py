from __future__ import annotations

from collections.abc import AsyncIterator

from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.config import LLMConfig
from app.services.llm.models import LLMRequest, LLMResponse, LLMStreamChunk, Usage


class MockProvider(BaseLLMProvider):
    """Local mock provider for CI and local development.

    Returns deterministic text without making any external network calls.
    """

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=self._config.mock_response,
            model=self._config.model,
            finish_reason="stop",
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        chunks = self._config.mock_stream_chunks or ["mock", " ", "answer"]
        for chunk in chunks:
            yield LLMStreamChunk(delta=chunk)
        yield LLMStreamChunk(delta="", finish_reason="stop")

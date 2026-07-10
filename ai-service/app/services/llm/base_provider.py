from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.services.llm.config import LLMConfig
from app.services.llm.models import LLMRequest, LLMResponse, LLMStreamChunk


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers that support sync and streaming completion."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a single complete response for ``request``."""
        ...

    @abstractmethod
    def stream_complete(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        """Yield incremental chunks for ``request``."""
        ...

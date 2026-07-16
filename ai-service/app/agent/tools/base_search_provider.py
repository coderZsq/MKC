from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.web_search import WebSearchRequest, WebSearchResult


class BaseSearchProvider(ABC):
    """Provider contract for web search backends."""

    @abstractmethod
    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """Search the web and return normalized results."""

    @abstractmethod
    def parse_response(self, raw: dict[str, Any], top_k: int) -> list[WebSearchResult]:
        """Parse provider-specific JSON into normalized results."""

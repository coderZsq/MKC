from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WebSearchRequest(BaseModel):
    """Request for an external web search."""

    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=10)


class WebSearchResult(BaseModel):
    """A normalized web search result."""

    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    snippet: str = ""


class WebSearchResponse(BaseModel):
    """Response returned by the web search tool."""

    results: list[WebSearchResult]
    source_type: Literal["web"] = "web"
    fallback: bool = False

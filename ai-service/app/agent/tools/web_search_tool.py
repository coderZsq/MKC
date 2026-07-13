from __future__ import annotations

from typing import Any


class WebSearchTool:
    """Optional S4-8 tool placeholder.

    The real web search implementation lands in S4-8. This wrapper keeps the
    Agent workflow contract stable and safely returns no external results.
    """

    async def invoke(self, query: str) -> list[dict[str, Any]]:
        return []

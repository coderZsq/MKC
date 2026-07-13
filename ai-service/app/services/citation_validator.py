from __future__ import annotations

import logging

from app.models.citation import Citation

logger = logging.getLogger(__name__)


class CitationValidator:
    """Validate grounded and authorized citations."""

    def __init__(self, max_citations: int = 8, log_dropped: bool = True) -> None:
        self._max_citations = max_citations
        self._log_dropped = log_dropped

    def validate(
        self,
        citations: list[Citation],
        authorized_resource_ids: set[str],
    ) -> list[Citation]:
        valid: list[Citation] = []
        for citation in citations:
            if citation.resource_id not in authorized_resource_ids:
                self._log_drop("unauthorized", citation)
                continue
            valid.append(citation)
            if len(valid) >= self._max_citations:
                break
        return valid

    def _log_drop(self, reason: str, citation: Citation) -> None:
        if self._log_dropped:
            logger.info(
                "drop citation",
                extra={"reason": reason, "citation_index": citation.index},
            )

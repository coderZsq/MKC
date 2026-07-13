from __future__ import annotations

import logging

from app.models.citation import Citation, CitationResult
from app.models.retrieval import RetrievalChunk
from app.services.citation_formatter import CitationFormatter
from app.services.citation_validator import CitationValidator

logger = logging.getLogger(__name__)


class CitationService:
    """Build validated citations from an answer and retrieved chunks."""

    def __init__(
        self,
        formatter: CitationFormatter,
        validator: CitationValidator,
    ) -> None:
        self._formatter = formatter
        self._validator = validator

    def build_citations(
        self,
        answer: str,
        chunks: list[RetrievalChunk],
        authorized_resource_ids: set[str],
    ) -> CitationResult:
        try:
            formatted = self._formatter.format(answer, chunks)
            citations = self._validator.validate(formatted.citations, authorized_resource_ids)
            return CitationResult(answer=formatted.answer, citations=citations)
        except Exception:
            logger.exception("citation mapping failed")
            return CitationResult(answer=answer, citations=[])


def format_timestamp(seconds: float) -> str:
    """Format seconds as mm:ss."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def citation_to_event_data(citation: Citation) -> dict:
    """Serialize a Citation into the S4-5 SSE citation event contract."""
    return citation.model_dump(exclude_none=True)

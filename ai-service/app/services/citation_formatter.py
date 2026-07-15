from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import Literal

from app.models.citation import Citation, CitationResult
from app.models.retrieval import RetrievalChunk

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Map Markdown footnote markers in an answer to retrieval chunk metadata."""

    def __init__(self, marker_pattern: str = r"\[\^(\d+)\]", snippet_max_chars: int = 200) -> None:
        self._pattern = re.compile(marker_pattern)
        self._snippet_max_chars = snippet_max_chars

    def format(self, answer: str, chunks: Sequence[RetrievalChunk]) -> CitationResult:
        used_indices: set[int] = set()
        citations: list[Citation] = []
        marker_replacements: dict[int, int] = {}

        for match in self._pattern.finditer(answer):
            index = int(match.group(1))
            if index in used_indices:
                continue
            if index < 1 or index > len(chunks):
                logger.info("drop out-of-range citation marker", extra={"citation_index": index})
                continue
            chunk = chunks[index - 1]
            citation_index = len(citations) + 1
            citations.append(self._citation_from_chunk(citation_index, index, chunk))
            marker_replacements[index] = citation_index
            used_indices.add(index)

        return CitationResult(
            answer=self._renumber_answer(answer, marker_replacements),
            citations=citations,
        )

    def _citation_from_chunk(
        self, index: int, original_index: int, chunk: RetrievalChunk
    ) -> Citation:
        metadata = chunk.metadata or {}
        resource_type = self._resource_type(metadata)
        return Citation(
            index=index,
            chunk_id=chunk.chunk_id,
            resource_id=chunk.resource_id,
            resource_type=resource_type,
            original_index=self._optional_original_index(index, original_index),
            page=self._optional_int(metadata.get("page")),
            timestamp_start=self._optional_float(
                metadata.get("timestamp_start", metadata.get("start_time"))
            ),
            timestamp_end=self._optional_float(
                metadata.get("timestamp_end", metadata.get("end_time"))
            ),
            score=chunk.score,
            snippet=self._truncate(chunk.text),
        )

    def _optional_original_index(self, index: int, original_index: int) -> int | None:
        return None if original_index == index else original_index

    def _resource_type(self, metadata: dict) -> Literal["audio", "pdf"]:
        raw = (
            metadata.get("resource_type")
            or metadata.get("content_type")
            or metadata.get("source_type")
            or "pdf"
        )
        if str(raw).lower() in {"audio", "media"}:
            return "audio"
        return "pdf"

    def _renumber_answer(self, answer: str, marker_replacements: dict[int, int]) -> str:
        if not marker_replacements:
            return answer

        def replace(match: re.Match[str]) -> str:
            original = int(match.group(1))
            replacement = marker_replacements.get(original)
            if replacement is None:
                return match.group(0)
            return f"[^{replacement}]"

        return self._pattern.sub(replace, answer)

    def _truncate(self, text: str) -> str:
        return text[: self._snippet_max_chars]

    def _optional_int(self, value: object) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if not isinstance(value, str):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _optional_float(self, value: object) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, int | float):
            return float(value)
        if not isinstance(value, str):
            return None
        try:
            return float(value)
        except ValueError:
            return None

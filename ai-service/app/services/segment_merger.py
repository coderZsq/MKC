from __future__ import annotations

import logging

from app.models.asr import AsrSegment

logger = logging.getLogger(__name__)


def _join_text(left: str, right: str, language: str | None) -> str:
    """Join two subtitle texts using language-appropriate spacing."""
    if language in {"zh", "zh-cn", "zh-tw", "ja", "ko"}:
        return left + right
    return f"{left} {right}".strip()


def _split_long_segment(segment: AsrSegment, max_chars: int) -> list[AsrSegment]:
    """Split a segment whose text exceeds ``max_chars`` into shorter pieces.

    Time is distributed proportionally to character count.
    """
    text = segment.text
    if len(text) <= max_chars:
        return [segment]

    chunks: list[str] = []
    for i in range(0, len(text), max_chars):
        chunks.append(text[i : i + max_chars])

    duration = max(segment.end - segment.start, 0.0)
    total_chars = len(text)
    pieces: list[AsrSegment] = []
    current_start = segment.start
    for idx, chunk in enumerate(chunks):
        if idx == len(chunks) - 1:
            end = segment.end
        else:
            ratio = len(chunk) / total_chars if total_chars else 1.0 / len(chunks)
            end = min(current_start + duration * ratio, segment.end)
        pieces.append(
            AsrSegment(
                start=current_start,
                end=end,
                text=chunk,
                confidence=segment.confidence,
            )
        )
        current_start = end
    return pieces


class SegmentMerger:
    """Merge adjacent short ASR segments and split overly long ones."""

    def __init__(
        self,
        min_duration: float = 1.0,
        max_duration: float = 6.0,
        max_chars: int = 80,
        language: str | None = None,
    ) -> None:
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_chars = max_chars
        self.language = language

    def merge(self, segments: list[AsrSegment]) -> list[AsrSegment]:
        """Merge ``segments`` into subtitle-ready pieces."""
        if not segments:
            return []

        normalized = self._normalize(segments)
        if not normalized:
            return []

        merged: list[AsrSegment] = []
        current = normalized[0].model_copy()

        for segment in normalized[1:]:
            candidate_duration = segment.end - current.start
            candidate_text = _join_text(current.text, segment.text, self.language)
            candidate_chars = len(candidate_text)

            should_merge = candidate_duration < self.min_duration or (
                candidate_duration < self.max_duration and candidate_chars < self.max_chars
            )

            if should_merge:
                current.end = segment.end
                current.text = candidate_text
                continue

            merged.extend(self._ensure_max_chars(current))
            current = segment.model_copy()

        merged.extend(self._ensure_max_chars(current))
        return merged

    def _normalize(self, segments: list[AsrSegment]) -> list[AsrSegment]:
        """Sort segments and fix invalid timestamps."""
        sorted_segments = sorted(segments, key=lambda seg: seg.start)
        normalized: list[AsrSegment] = []
        for segment in sorted_segments:
            start = max(segment.start, 0.0)
            end = segment.end
            if end < start:
                logger.warning(
                    "fixed negative duration segment: start=%s end=%s",
                    segment.start,
                    segment.end,
                )
                end = start
            normalized.append(segment.model_copy(update={"start": start, "end": end}))
        return normalized

    def _ensure_max_chars(self, segment: AsrSegment) -> list[AsrSegment]:
        """Split a segment if its text exceeds the maximum character count."""
        if len(segment.text) <= self.max_chars:
            return [segment]
        return _split_long_segment(segment, self.max_chars)

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from app.models.asr import AsrSegment

logger = logging.getLogger(__name__)

DEFAULT_FILLER_WORDS = [
    "嗯",
    "啊",
    "哦",
    "呃",
    "那个",
    "就是",
    "然后",
    "这个",
    "那個",
    "這個",
]

# Matches word repetitions separated by spaces (e.g. "hello hello hello").
_WORD_REPEAT_PATTERN = re.compile(r"(\b\w+\b)(\s+\1){2,}")


class RuleCleaner:
    """Fast rule-based text cleaning for ASR segments.

    Removes filler words, stutters, and adjacent repeated characters/words.
    Timestamps are not modified: the cleaner returns new ``AsrSegment`` instances.
    """

    def __init__(self, filler_words: Sequence[str] | None = None) -> None:
        self.filler_words = list(filler_words) if filler_words else list(DEFAULT_FILLER_WORDS)

    def clean(self, text: str) -> str:
        """Return a cleaned copy of ``text``."""
        cleaned = text
        cleaned = self._remove_word_repetitions(cleaned)
        cleaned = self._remove_filler_words(cleaned)
        cleaned = self._collapse_adjacent_repeats(cleaned)
        cleaned = self._normalize_whitespace(cleaned)
        return cleaned.strip()

    def clean_segments(self, segments: list[AsrSegment]) -> list[AsrSegment]:
        """Return a new list of segments with cleaned text and original timestamps."""
        return [
            segment.model_copy(update={"text": self.clean(segment.text)}) for segment in segments
        ]

    def _remove_word_repetitions(self, text: str) -> str:
        return _WORD_REPEAT_PATTERN.sub(r"\1", text)

    def _remove_filler_words(self, text: str) -> str:
        cleaned = text
        for word in self.filler_words:
            cleaned = cleaned.replace(word, "")
        return cleaned

    def _collapse_adjacent_repeats(self, text: str) -> str:
        """Collapse runs of the same character or short syllable (e.g. "是是是" -> "是")."""
        cleaned = text
        # CJK characters repeated 3+ times consecutively (no spaces).
        cleaned = re.sub(r"([一-鿿])\1{2,}", r"\1", cleaned)
        # CJK characters repeated 2+ times with spaces in between.
        cleaned = re.sub(r"([一-鿿])(?:\s+\1){2,}", r"\1", cleaned)
        # Short alphabetic/word tokens repeated 3+ times consecutively (no spaces).
        cleaned = re.sub(r"(\b\w{1,4}\b)\1{2,}", r"\1", cleaned)
        return cleaned

    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text)

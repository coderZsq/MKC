from __future__ import annotations

import logging
from typing import Any

from app.core.exceptions import TextCleaningError
from app.models.asr import AsrSegment
from app.services.text_cleaning.llm_cleaner import LlmCleaner
from app.services.text_cleaning.rule_cleaner import RuleCleaner

logger = logging.getLogger(__name__)


class TextCleaningService:
    """Orchestrates rule-based and optional LLM-based text cleaning.

    The service preserves the original timestamps of every segment. On any error
    it falls back to the input segments unless ``fallback_on_error`` is disabled.
    """

    MODE_RULE = "rule"
    MODE_LLM = "llm"
    MODE_HYBRID = "hybrid"
    SUPPORTED_MODES = {MODE_RULE, MODE_LLM, MODE_HYBRID}

    def __init__(
        self,
        rule_cleaner: RuleCleaner,
        llm_cleaner: LlmCleaner | None,
        config: dict[str, Any],
    ) -> None:
        self.rule_cleaner = rule_cleaner
        self.llm_cleaner = llm_cleaner
        self.config = config

    @property
    def mode(self) -> str:
        mode = str(self.config.get("mode", self.MODE_RULE)).lower().strip()
        return mode if mode in self.SUPPORTED_MODES else self.MODE_RULE

    @property
    def fallback_on_error(self) -> bool:
        return bool(self.config.get("fallback_on_error", True))

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", True))

    def clean(self, segments: list[AsrSegment]) -> list[AsrSegment]:
        """Clean ``segments`` according to the configured mode and return a new list."""
        if not self.enabled or not segments:
            return list(segments)

        original = [segment.model_copy() for segment in segments]
        try:
            cleaned = self.rule_cleaner.clean_segments(segments)
            if self.mode in (self.MODE_LLM, self.MODE_HYBRID):
                if self.llm_cleaner is None:
                    logger.warning(
                        "text cleaning mode is %s but no LLM cleaner is configured",
                        self.mode,
                    )
                else:
                    cleaned = self.llm_cleaner.clean_segments(cleaned)
            return self._validate(cleaned, original)
        except Exception as exc:
            if self.fallback_on_error:
                logger.warning("text cleaning failed, falling back to original ASR text: %s", exc)
                return original
            logger.exception("text cleaning failed and fallback is disabled")
            raise TextCleaningError(
                "LLM_CLEAN_FAILED",
                "文本清洗失败，已使用原始文本",
                500,
            ) from exc

    @staticmethod
    def _validate(
        cleaned: list[AsrSegment],
        original: list[AsrSegment],
    ) -> list[AsrSegment]:
        """Ensure the cleaned segments are valid and non-empty."""
        if len(cleaned) != len(original):
            raise ValueError(
                f"cleaned segment count {len(cleaned)} does not match original {len(original)}"
            )
        for segment in cleaned:
            if not segment.text.strip():
                raise TextCleaningError(
                    "EMPTY_AFTER_CLEAN",
                    "清洗后文本为空，回退原始",
                    500,
                )
        return cleaned

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import TextCleaningError
from app.models.asr import AsrSegment
from app.services.text_cleaning import LlmCleaner, RuleCleaner, TextCleaningService


class TestTextCleaningService:
    @pytest.fixture
    def rule_cleaner(self) -> RuleCleaner:
        return RuleCleaner()

    @pytest.fixture
    def segments(self) -> list[AsrSegment]:
        return [
            AsrSegment(start=0.0, end=1.0, text="嗯今天"),
            AsrSegment(start=1.0, end=2.0, text="啊啊天气"),
        ]

    def test_rule_mode_only(self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]) -> None:
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=None,
            config={"mode": "rule"},
        )
        cleaned = service.clean(segments)

        assert cleaned[0].text == "今天"
        assert cleaned[1].text == "天气"
        assert cleaned[0].start == 0.0
        assert cleaned[1].end == 2.0

    def test_llm_mode_calls_llm_cleaner(
        self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]
    ) -> None:
        llm_cleaner = MagicMock(spec=LlmCleaner)
        llm_cleaner.clean_segments.return_value = [
            AsrSegment(start=0.0, end=1.0, text="今天真热"),
            AsrSegment(start=1.0, end=2.0, text="天气很好"),
        ]
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=llm_cleaner,
            config={"mode": "llm"},
        )
        cleaned = service.clean(segments)

        llm_cleaner.clean_segments.assert_called_once()
        assert cleaned[0].text == "今天真热"
        assert cleaned[1].text == "天气很好"

    def test_hybrid_mode_calls_both(
        self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]
    ) -> None:
        llm_cleaner = MagicMock(spec=LlmCleaner)
        llm_cleaner.clean_segments.return_value = [
            AsrSegment(start=0.0, end=1.0, text="今天"),
            AsrSegment(start=1.0, end=2.0, text="天气"),
        ]
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=llm_cleaner,
            config={"mode": "hybrid"},
        )
        service.clean(segments)

        # Rule cleaner runs first, then LLM cleaner receives rule-cleaned segments.
        passed_to_llm = llm_cleaner.clean_segments.call_args[0][0]
        assert passed_to_llm[0].text == "今天"
        assert passed_to_llm[1].text == "天气"

    def test_disabled_returns_original(
        self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]
    ) -> None:
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=None,
            config={"enabled": False, "mode": "rule"},
        )
        cleaned = service.clean(segments)

        assert cleaned[0].text == "嗯今天"
        assert cleaned[1].text == "啊啊天气"

    def test_empty_segments_returns_empty(self, rule_cleaner: RuleCleaner) -> None:
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=None,
            config={"mode": "rule"},
        )
        assert service.clean([]) == []

    def test_fallback_on_llm_error(
        self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]
    ) -> None:
        llm_cleaner = MagicMock(spec=LlmCleaner)
        llm_cleaner.clean_segments.side_effect = RuntimeError("LLM down")
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=llm_cleaner,
            config={"mode": "llm", "fallback_on_error": True},
        )
        cleaned = service.clean(segments)

        # On any cleaning failure, fall back to the original ASR text.
        assert cleaned[0].text == "嗯今天"
        assert cleaned[1].text == "啊啊天气"
        assert cleaned[0].start == 0.0
        assert cleaned[1].end == 2.0

    def test_no_fallback_raises_on_error(
        self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]
    ) -> None:
        llm_cleaner = MagicMock(spec=LlmCleaner)
        llm_cleaner.clean_segments.side_effect = RuntimeError("LLM down")
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=llm_cleaner,
            config={"mode": "llm", "fallback_on_error": False},
        )

        with pytest.raises(TextCleaningError):
            service.clean(segments)

    def test_fallback_on_empty_text(self, rule_cleaner: RuleCleaner) -> None:
        segments = [
            AsrSegment(start=0.0, end=1.0, text="嗯"),
            AsrSegment(start=1.0, end=2.0, text="啊"),
        ]
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=None,
            config={"mode": "rule", "fallback_on_error": True},
        )
        cleaned = service.clean(segments)

        # Validation fails because rule cleaning makes text empty, so we fall back.
        assert cleaned[0].text == "嗯"
        assert cleaned[1].text == "啊"

    def test_invalid_mode_defaults_to_rule(
        self, rule_cleaner: RuleCleaner, segments: list[AsrSegment]
    ) -> None:
        service = TextCleaningService(
            rule_cleaner=rule_cleaner,
            llm_cleaner=None,
            config={"mode": "unknown"},
        )
        cleaned = service.clean(segments)

        assert cleaned[0].text == "今天"

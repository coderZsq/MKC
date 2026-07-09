from __future__ import annotations

import pytest

from app.models.asr import AsrSegment
from app.services.text_cleaning.rule_cleaner import RuleCleaner


class TestRuleCleaner:
    @pytest.fixture
    def cleaner(self) -> RuleCleaner:
        return RuleCleaner()

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("嗯，今天天气真好啊", "，今天天气真好"),
            ("哦，我知道了呃", "，我知道了"),
            ("那个，我想说的就是", "，我想说的"),
        ],
    )
    def test_removes_filler_words(self, cleaner: RuleCleaner, raw: str, expected: str) -> None:
        assert cleaner.clean(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("是是是", "是"),
            ("好好好", "好"),
            ("对对对对", "对"),
        ],
    )
    def test_collapses_chinese_repeats(self, cleaner: RuleCleaner, raw: str, expected: str) -> None:
        assert cleaner.clean(raw) == expected

    def test_removes_word_repetitions(self, cleaner: RuleCleaner) -> None:
        assert cleaner.clean("hello hello hello world") == "hello world"

    def test_preserves_timestamps_in_segments(self, cleaner: RuleCleaner) -> None:
        segments = [
            AsrSegment(start=0.0, end=1.0, text="嗯，今天"),
            AsrSegment(start=1.0, end=2.0, text="啊啊，天气真好"),
        ]
        cleaned = cleaner.clean_segments(segments)

        assert len(cleaned) == 2
        assert cleaned[0].start == 0.0
        assert cleaned[0].end == 1.0
        assert cleaned[0].text == "，今天"
        assert cleaned[1].start == 1.0
        assert cleaned[1].end == 2.0
        assert cleaned[1].text == "，天气真好"

        # Original segments are not mutated.
        assert segments[0].text == "嗯，今天"

    def test_custom_filler_words(self) -> None:
        cleaner = RuleCleaner(filler_words=["对吧"])
        assert cleaner.clean("对吧，这是对的") == "，这是对的"

    def test_empty_text_returns_empty(self, cleaner: RuleCleaner) -> None:
        assert cleaner.clean("") == ""

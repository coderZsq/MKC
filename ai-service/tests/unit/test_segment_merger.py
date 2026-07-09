from __future__ import annotations

import pytest

from app.models.asr import AsrSegment
from app.services.segment_merger import SegmentMerger, _join_text


class TestSegmentMerger:
    @pytest.fixture
    def merger(self) -> SegmentMerger:
        return SegmentMerger(min_duration=1.0, max_duration=6.0, max_chars=80, language="zh")

    def test_merge_empty_segments(self, merger: SegmentMerger) -> None:
        assert merger.merge([]) == []

    def test_merge_short_adjacent_segments(self, merger: SegmentMerger) -> None:
        segments = [
            AsrSegment(start=0.0, end=0.3, text="你好"),
            AsrSegment(start=0.4, end=0.7, text="世界"),
            AsrSegment(start=0.8, end=1.5, text="欢迎"),
        ]
        merged = merger.merge(segments)
        assert len(merged) == 1
        assert merged[0].start == 0.0
        assert merged[0].end == 1.5
        assert merged[0].text == "你好世界欢迎"

    def test_merge_does_not_exceed_max_duration(self, merger: SegmentMerger) -> None:
        segments = [
            AsrSegment(start=0.0, end=2.0, text="a"),
            AsrSegment(start=2.1, end=5.0, text="b"),
            AsrSegment(start=5.1, end=6.0, text="c"),
        ]
        merged = merger.merge(segments)
        assert len(merged) == 2
        assert merged[0].end == 5.0
        assert merged[1].start == 5.1

    def test_merge_splits_long_text(self, merger: SegmentMerger) -> None:
        long_text = "a" * 100
        segments = [AsrSegment(start=0.0, end=2.0, text=long_text)]
        merged = merger.merge(segments)
        assert len(merged) > 1
        assert all(len(seg.text) <= 80 for seg in merged)

    def test_merge_sorts_unordered_segments(self, merger: SegmentMerger) -> None:
        segments = [
            AsrSegment(start=8.0, end=9.0, text="b"),
            AsrSegment(start=0.0, end=1.0, text="a"),
        ]
        merged = merger.merge(segments)
        assert merged[0].text == "a"
        assert merged[1].text == "b"

    def test_merge_fixes_negative_duration(self, merger: SegmentMerger) -> None:
        segments = [AsrSegment(start=2.0, end=1.0, text="broken")]
        merged = merger.merge(segments)
        assert len(merged) == 1
        assert merged[0].start == 2.0
        assert merged[0].end == 2.0

    def test_merge_respects_language_spacing(self) -> None:
        english_merger = SegmentMerger(language="en")
        segments = [
            AsrSegment(start=0.0, end=1.0, text="hello"),
            AsrSegment(start=1.1, end=2.0, text="world"),
        ]
        merged = english_merger.merge(segments)
        assert merged[0].text == "hello world"

    def test_join_text_cjk_concatenates(self) -> None:
        assert _join_text("你好", "世界", "zh") == "你好世界"

    def test_join_text_english_adds_space(self) -> None:
        assert _join_text("hello", "world", "en") == "hello world"

from __future__ import annotations

from app.utils.timecode import format_timecode


class TestFormatTimecode:
    def test_standard_srt_timecode(self) -> None:
        assert format_timecode(5.0) == "00:00:05,000"
        assert format_timecode(8.2) == "00:00:08,200"

    def test_hours_minutes_seconds(self) -> None:
        assert format_timecode(3661.123) == "01:01:01,123"

    def test_vtt_timecode_uses_dot_separator(self) -> None:
        assert format_timecode(5.0, separator=".") == "00:00:05.000"

    def test_negative_time_is_clamped_to_zero(self) -> None:
        assert format_timecode(-1.5) == "00:00:00,000"

    def test_millisecond_rounding(self) -> None:
        assert format_timecode(0.9995) == "00:00:01,000"

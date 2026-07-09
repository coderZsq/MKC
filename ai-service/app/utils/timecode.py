from __future__ import annotations


def format_timecode(seconds: float, separator: str = ",") -> str:
    """Format a timestamp in seconds as ``HH:MM:SS{separator}mmm``.

    Args:
        seconds: Timestamp in seconds. Values below zero are clamped to zero.
        separator: Millisecond separator. Use a comma for SRT (default) or a
            dot for WebVTT.

    Returns:
        Formatted timecode string.
    """
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, millis = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"

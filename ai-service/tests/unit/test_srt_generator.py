from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import SubtitleGenerationError
from app.models.asr import AsrSegment
from app.services.srt_generator import SUPPORTED_FORMATS, SrtGenerator


class TestSrtGenerator:
    @pytest.fixture
    def generator(self) -> SrtGenerator:
        return SrtGenerator(
            min_duration=1.0,
            max_duration=6.0,
            max_chars=80,
            output_format="srt",
        )

    @pytest.fixture
    def segments(self) -> list[AsrSegment]:
        return [
            AsrSegment(start=5.0, end=8.2, text="大家好"),
            AsrSegment(start=8.2, end=12.5, text="欢迎参加"),
        ]

    def test_supported_formats(self) -> None:
        assert {"srt", "vtt"} == SUPPORTED_FORMATS

    def test_generate_standard_srt(
        self, generator: SrtGenerator, segments: list[AsrSegment]
    ) -> None:
        srt = generator.generate(segments, language="zh")
        assert "1\n00:00:05,000 --> 00:00:08,200\n大家好\n" in srt
        assert "2\n00:00:08,200 --> 00:00:12,500\n欢迎参加\n" in srt

    def test_generate_merges_short_segments(self, generator: SrtGenerator) -> None:
        segments = [
            AsrSegment(start=0.0, end=0.4, text="你好"),
            AsrSegment(start=0.5, end=0.9, text="世界"),
        ]
        srt = generator.generate(segments, language="zh")
        assert "1\n00:00:00,000 --> 00:00:00,900\n你好世界\n" in srt

    def test_generate_splits_long_text(self, generator: SrtGenerator) -> None:
        long_text = "a" * 100
        segments = [AsrSegment(start=0.0, end=2.0, text=long_text)]
        srt = generator.generate(segments)
        blocks = [block for block in srt.split("\n\n") if block]
        assert len(blocks) > 1
        for block in blocks:
            lines = block.split("\n")
            assert len(lines[2]) <= 80

    def test_generate_empty_segments_raises(self, generator: SrtGenerator) -> None:
        with pytest.raises(SubtitleGenerationError) as exc_info:
            generator.generate([])
        assert exc_info.value.code == "EMPTY_SEGMENTS"

    def test_generate_vtt_format(self) -> None:
        vtt_generator = SrtGenerator(output_format="vtt")
        segments = [AsrSegment(start=1.0, end=3.0, text="hello")]
        vtt = vtt_generator.generate(segments, language="en")
        assert vtt.startswith("WEBVTT\n")
        assert "00:00:01.000 --> 00:00:03.000" in vtt

    def test_invalid_output_format_raises(self) -> None:
        with pytest.raises(SubtitleGenerationError) as exc_info:
            SrtGenerator(output_format="ass")
        assert exc_info.value.code == "INVALID_OUTPUT_FORMAT"

    def test_save_to_minio_returns_minio_uri(self, generator: SrtGenerator) -> None:
        mock_client = MagicMock()
        content = "1\n00:00:00,000 --> 00:00:01,000\nhello\n"

        with patch(
            "app.services.srt_generator._build_minio_client",
            return_value=mock_client,
        ):
            url = generator.save_to_minio(content, "results/task-1/subtitle.srt")

        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args
        assert call_args.args[0] == "mkc-resources"
        assert call_args.args[1] == "results/task-1/subtitle.srt"
        assert isinstance(call_args.args[2], BytesIO)
        assert call_args.kwargs["length"] == len(content.encode("utf-8"))
        assert url == "minio://mkc-resources/results/task-1/subtitle.srt"

    def test_save_to_minio_failure_raises_storage_error(self, generator: SrtGenerator) -> None:
        mock_client = MagicMock()
        mock_client.put_object.side_effect = RuntimeError("connection refused")

        with (
            patch(
                "app.services.srt_generator._build_minio_client",
                return_value=mock_client,
            ),
            pytest.raises(SubtitleGenerationError) as exc_info,
        ):
            generator.save_to_minio("content", "results/task-1/subtitle.srt")

        assert exc_info.value.code == "STORAGE_ERROR"

    def test_save_to_minio_presigned_expiry_at_least_one_hour(
        self, generator: SrtGenerator
    ) -> None:
        mock_client = MagicMock()

        with patch(
            "app.services.srt_generator._build_minio_client",
            return_value=mock_client,
        ):
            generator.save_to_minio("content", "key")

        mock_client.put_object.assert_called_once()

    def test_srt_is_parseable_into_blocks(self, generator: SrtGenerator) -> None:
        segments = [
            AsrSegment(start=1.0, end=2.0, text="first"),
            AsrSegment(start=8.0, end=9.0, text="second"),
        ]
        srt = generator.generate(segments, language="en")
        blocks = [block for block in srt.split("\n\n") if block]
        assert len(blocks) == 2
        for index, block in enumerate(blocks, start=1):
            lines = block.split("\n")
            assert lines[0] == str(index)
            assert "-->" in lines[1]
            assert lines[2]

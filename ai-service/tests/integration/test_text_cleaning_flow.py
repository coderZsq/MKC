from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.asr import AsrResult, AsrSegment, AsrTaskRequest
from app.services.asr_service import AsrService
from app.services.text_cleaning import TextCleaningService


@pytest.fixture
def fake_engine() -> MagicMock:
    engine = MagicMock()
    engine.transcribe.return_value = iter(
        [
            {"start": 0.0, "end": 2.0, "text": "嗯，今天天气", "confidence": -0.5},
            {"start": 2.5, "end": 4.5, "text": "啊啊，很好", "confidence": -0.6},
        ]
    )
    return engine


@pytest.fixture
def fake_processor() -> MagicMock:
    processor = MagicMock()
    processor.convert_to_wav.return_value = Path("/tmp/converted.wav")
    processor.get_duration.return_value = 10.0
    return processor


@pytest.fixture
def fake_reporter() -> MagicMock:
    return MagicMock()


@pytest.fixture
def fake_subtitle_generator() -> MagicMock:
    generator = MagicMock()
    generator.output_format = "srt"
    generator.generate.return_value = "1\n00:00:00,000 --> 00:00:02,000\n今天天气\n"
    generator.save_to_minio.return_value = "http://minio/results/task-1/subtitle.srt"
    return generator


class TestTextCleaningFlow:
    def test_cleaned_text_used_in_result_and_subtitle(
        self,
        fake_engine: MagicMock,
        fake_processor: MagicMock,
        fake_reporter: MagicMock,
        fake_subtitle_generator: MagicMock,
    ) -> None:
        cleaning_service = TextCleaningService(
            rule_cleaner=MagicMock(),
            llm_cleaner=None,
            config={"mode": "rule"},
        )
        # Override rule cleaner behavior so we can assert it runs.
        cleaning_service.rule_cleaner.clean_segments = lambda segments: [
            segment.model_copy(update={"text": segment.text.replace("嗯", "").replace("啊", "")})
            for segment in segments
        ]

        service = AsrService(
            engine=fake_engine,
            processor=fake_processor,
            reporter=fake_reporter,
            download_func=lambda _url, target: target.write_text("fake"),
            progress_interval=0.0,
            subtitle_generator=fake_subtitle_generator,
            text_cleaning_service=cleaning_service,
        )
        task = AsrTaskRequest(
            task_id="task-1",
            resource_id="res-1",
            audio_url="minio://resources/audio.mp3",
            language="zh",
        )

        result = service.process(task)

        assert isinstance(result, AsrResult)
        assert result.text == "，今天天气，很好"
        assert len(result.segments) == 2
        assert result.segments[0].text == "，今天天气"
        assert result.segments[1].text == "，很好"
        fake_subtitle_generator.generate.assert_called_once()
        fake_subtitle_generator.save_to_minio.assert_called_once()

    @patch("app.services.asr_service._default_text_cleaning_service")
    def test_default_service_cleans_segments(
        self,
        mock_default_cleaning: MagicMock,
        fake_engine: MagicMock,
        fake_processor: MagicMock,
        fake_reporter: MagicMock,
        fake_subtitle_generator: MagicMock,
    ) -> None:
        cleaning_service = MagicMock()
        cleaning_service.clean.return_value = [
            AsrSegment(start=0.0, end=2.0, text="今天天气"),
            AsrSegment(start=2.5, end=4.5, text="很好"),
        ]
        mock_default_cleaning.return_value = cleaning_service

        service = AsrService(
            engine=fake_engine,
            processor=fake_processor,
            reporter=fake_reporter,
            download_func=lambda _url, target: target.write_text("fake"),
            progress_interval=0.0,
            subtitle_generator=fake_subtitle_generator,
        )
        task = AsrTaskRequest(
            task_id="task-1",
            resource_id="res-1",
            audio_url="minio://resources/audio.mp3",
            language="zh",
        )

        result = service.process(task)

        cleaning_service.clean.assert_called_once()
        assert result.text == "今天天气很好"
        assert result.segments[0].text == "今天天气"

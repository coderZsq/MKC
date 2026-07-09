from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.asr import AsrResult, AsrTaskRequest
from app.services.asr_service import AsrService
from app.services.audio_processor import AudioProcessor
from app.services.whisper_engine import WhisperEngine


@pytest.fixture
def fake_engine() -> MagicMock:
    engine = MagicMock(spec=WhisperEngine)
    engine.transcribe.return_value = iter(
        [
            {"start": 0.0, "end": 2.0, "text": "你好", "confidence": -0.5},
            {"start": 2.5, "end": 4.5, "text": "世界", "confidence": -0.6},
        ]
    )
    return engine


@pytest.fixture
def fake_processor() -> MagicMock:
    processor = MagicMock(spec=AudioProcessor)
    processor.convert_to_wav.return_value = Path("/tmp/converted.wav")
    processor.get_duration.return_value = 10.0
    return processor


@pytest.fixture
def fake_reporter() -> MagicMock:
    return MagicMock()


@patch("app.services.srt_generator._build_minio_client")
@patch("app.services.asr_service._default_subtitle_generator")
def test_asr_flow_generates_and_uploads_subtitle(
    mock_default_generator: MagicMock,
    mock_build_minio_client: MagicMock,
    fake_engine: MagicMock,
    fake_processor: MagicMock,
    fake_reporter: MagicMock,
) -> None:
    from app.services.srt_generator import SrtGenerator

    mock_minio_client = MagicMock()
    mock_minio_client.presigned_get_object.return_value = "http://minio/results/task-1/subtitle.srt"
    mock_build_minio_client.return_value = mock_minio_client

    mock_default_generator.return_value = SrtGenerator(
        min_duration=1.0,
        max_duration=6.0,
        max_chars=80,
        output_format="srt",
    )

    service = AsrService(
        engine=fake_engine,
        processor=fake_processor,
        reporter=fake_reporter,
        download_func=lambda _url, target: target.write_text("fake"),
        progress_interval=0.0,
    )

    task = AsrTaskRequest(
        task_id="task-1",
        resource_id="res-1",
        audio_url="minio://resources/audio.mp3",
        language="zh",
    )
    result = service.process(task)

    assert isinstance(result, AsrResult)
    assert result.subtitle_url == "http://minio/results/task-1/subtitle.srt"
    mock_minio_client.put_object.assert_called_once()
    fake_reporter.mark_status.assert_any_call(
        "task-1",
        "completed",
        result=result.model_dump(),
    )


@patch("app.services.asr_service._default_subtitle_generator")
def test_asr_flow_reports_failure_on_subtitle_upload_error(
    mock_default_generator: MagicMock,
    fake_engine: MagicMock,
    fake_processor: MagicMock,
    fake_reporter: MagicMock,
) -> None:
    from app.core.exceptions import SubtitleGenerationError
    from app.services.srt_generator import SrtGenerator

    mock_default_generator.return_value = SrtGenerator(output_format="srt")

    with patch(
        "app.services.srt_generator._build_minio_client",
        side_effect=SubtitleGenerationError("STORAGE_ERROR", "字幕存储失败"),
    ):
        service = AsrService(
            engine=fake_engine,
            processor=fake_processor,
            reporter=fake_reporter,
            download_func=lambda _url, target: target.write_text("fake"),
            progress_interval=0.0,
        )

        task = AsrTaskRequest(
            task_id="task-2",
            resource_id="res-2",
            audio_url="minio://resources/audio.mp3",
        )
        with pytest.raises(SubtitleGenerationError):
            service.process(task)

    fake_reporter.mark_status.assert_called_with(
        "task-2",
        "failed",
        error_message="字幕存储失败",
    )

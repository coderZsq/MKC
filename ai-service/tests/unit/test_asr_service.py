from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AsrProcessingError, AudioProcessingError, SubtitleGenerationError
from app.models.asr import AsrResult, AsrSegment, AsrTaskRequest
from app.services.asr_service import AsrService
from app.services.gateway_reporter import GatewayProgressReporter


@pytest.fixture
def reporter() -> GatewayProgressReporter:
    return GatewayProgressReporter(
        base_url="http://gateway",
        internal_key="test-key",
    )


@pytest.fixture
def fake_subtitle_generator() -> MagicMock:
    generator = MagicMock()
    generator.output_format = "srt"
    generator.generate.return_value = "1\n00:00:00,000 --> 00:00:01,000\nhello\n"
    generator.save_to_minio.return_value = "minio://mkc-resources/results/task-1/subtitle.srt"
    return generator


@pytest.fixture
def fake_text_cleaning_service() -> MagicMock:
    cleaner = MagicMock()
    cleaner.clean.side_effect = lambda segments: segments
    return cleaner


class TestGatewayProgressReporter:
    def test_report_progress(self, reporter: GatewayProgressReporter) -> None:
        mock_patch = MagicMock()
        with patch("app.services.gateway_reporter.requests.patch", mock_patch):
            reporter.report_progress("task-1", 35, "running")

        mock_patch.assert_called_once_with(
            "http://gateway/api/v1/internal/tasks/task-1/progress",
            json={"progress": 35, "status": "running"},
            headers={"X-Internal-Key": "test-key"},
            timeout=5.0,
        )

    def test_mark_completed(self, reporter: GatewayProgressReporter) -> None:
        result = {"segments": [], "text": "hello"}
        mock_post = MagicMock()
        with patch("app.services.gateway_reporter.requests.post", mock_post):
            reporter.mark_status("task-1", "completed", result=result)

        mock_post.assert_called_once_with(
            "http://gateway/api/v1/internal/tasks/task-1/status",
            json={"status": "completed", "result": result, "error_message": None},
            headers={"X-Internal-Key": "test-key"},
            timeout=5.0,
        )

    def test_mark_failed(self, reporter: GatewayProgressReporter) -> None:
        mock_post = MagicMock()
        with patch("app.services.gateway_reporter.requests.post", mock_post):
            reporter.mark_status("task-1", "failed", error_message="boom")

        mock_post.assert_called_once_with(
            "http://gateway/api/v1/internal/tasks/task-1/status",
            json={"status": "failed", "result": None, "error_message": "boom"},
            headers={"X-Internal-Key": "test-key"},
            timeout=5.0,
        )

    def test_default_urls_from_config(self) -> None:
        with patch(
            "app.services.gateway_reporter.settings",
            MagicMock(
                ai_config={
                    "gateway": {
                        "base_url": "http://localhost:8080",
                        "progress_path": "/api/v1/internal/tasks/{task_id}/progress",
                        "status_path": "/api/v1/internal/tasks/{task_id}/status",
                    }
                },
                internal_api_key="cfg-key",
            ),
        ):
            default_reporter = GatewayProgressReporter()
            assert default_reporter._base_url == "http://localhost:8080"
            assert default_reporter._internal_key == "cfg-key"


class TestAsrService:
    @pytest.fixture
    def fake_engine(self) -> MagicMock:
        engine = MagicMock()
        engine.transcribe.return_value = iter(
            [
                {"start": 0.0, "end": 2.0, "text": "你好", "confidence": -0.5},
                {"start": 2.5, "end": 4.5, "text": "世界", "confidence": -0.6},
            ]
        )
        return engine

    @pytest.fixture
    def fake_processor(self) -> MagicMock:
        processor = MagicMock()
        processor.convert_to_wav.return_value = Path("/tmp/converted.wav")
        processor.get_duration.return_value = 10.0
        return processor

    @pytest.fixture
    def fake_reporter(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        fake_engine: MagicMock,
        fake_processor: MagicMock,
        fake_reporter: MagicMock,
        fake_subtitle_generator: MagicMock,
        fake_text_cleaning_service: MagicMock,
    ) -> AsrService:
        return AsrService(
            engine=fake_engine,
            processor=fake_processor,
            reporter=fake_reporter,
            download_func=lambda _url, target: target.write_text("fake"),
            progress_interval=0.0,
            subtitle_generator=fake_subtitle_generator,
            text_cleaning_service=fake_text_cleaning_service,
        )

    def test_process_success(
        self,
        service: AsrService,
        fake_engine: MagicMock,
        fake_reporter: MagicMock,
        fake_subtitle_generator: MagicMock,
    ) -> None:
        with patch("app.services.asr_service.upload_json") as upload_json_mock:
            upload_json_mock.return_value = "minio://mkc-resources/results/task-1/transcript.json"
            task = AsrTaskRequest(
                task_id="task-1",
                resource_id="res-1",
                audio_url="minio://resources/audio.mp3",
                language="zh",
                model="small",
            )

            result = service.process(task)

        assert isinstance(result, AsrResult)
        assert result.task_id == "task-1"
        assert result.resource_id == "res-1"
        assert result.text == "你好世界"
        assert len(result.segments) == 2
        assert result.segments[0] == AsrSegment(start=0.0, end=2.0, text="你好", confidence=-0.5)
        assert result.subtitle_url == "minio://mkc-resources/results/task-1/subtitle.srt"
        assert result.transcript_url == "minio://mkc-resources/results/task-1/transcript.json"
        fake_reporter.mark_status.assert_any_call("task-1", "running")
        fake_reporter.mark_status.assert_any_call(
            "task-1",
            "completed",
            result=result.model_dump(),
        )
        fake_subtitle_generator.generate.assert_called_once()
        fake_subtitle_generator.save_to_minio.assert_called_once()
        upload_json_mock.assert_called_once()

    def test_process_subtitle_generation_failure(
        self,
        service: AsrService,
        fake_subtitle_generator: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_subtitle_generator.save_to_minio.side_effect = SubtitleGenerationError(
            "STORAGE_ERROR", "字幕存储失败"
        )

        with patch("app.services.asr_service.upload_json") as upload_json_mock:
            upload_json_mock.return_value = "minio://mkc-resources/results/task-4/transcript.json"
            task = AsrTaskRequest(
                task_id="task-4",
                resource_id="res-4",
                audio_url="minio://resources/audio.mp3",
            )

            with pytest.raises(SubtitleGenerationError):
                service.process(task)

        fake_reporter.mark_status.assert_called_with(
            "task-4",
            "failed",
            error_message="字幕存储失败",
        )

    def test_process_download_failure(
        self,
        service: AsrService,
        fake_reporter: MagicMock,
    ) -> None:
        def fail_download(_url: str, _target: Path) -> None:
            raise AudioProcessingError("download failed")

        service._download_func = fail_download

        task = AsrTaskRequest(
            task_id="task-2",
            resource_id="res-2",
            audio_url="minio://missing/audio.mp3",
        )

        with pytest.raises(AudioProcessingError):
            service.process(task)

        fake_reporter.mark_status.assert_called_with(
            "task-2",
            "failed",
            error_message="download failed",
        )

    def test_process_transcription_failure(
        self,
        service: AsrService,
        fake_engine: MagicMock,
        fake_reporter: MagicMock,
    ) -> None:
        fake_engine.transcribe.side_effect = AsrProcessingError("inference failed")

        task = AsrTaskRequest(
            task_id="task-3",
            resource_id="res-3",
            audio_url="minio://resources/audio.mp3",
        )

        with pytest.raises(AsrProcessingError):
            service.process(task)

        fake_reporter.mark_status.assert_called_with(
            "task-3",
            "failed",
            error_message="transcription failed: inference failed",
        )

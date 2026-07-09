from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.exceptions import ModelLoadError
from celery_workers.tasks.asr_task import run_asr


def _task_payload(model: str = "large-v3") -> dict[str, str]:
    return {
        "task_id": "task-1",
        "resource_id": "res-1",
        "audio_url": "minio://resources/audio.mp3",
        "model": model,
    }


@patch("celery_workers.tasks.asr_task._build_engine")
@patch("celery_workers.tasks.asr_task.AudioProcessor")
@patch("celery_workers.tasks.asr_task.GatewayProgressReporter")
@patch("celery_workers.tasks.asr_task.AsrService")
@patch("celery_workers.tasks.asr_task.settings")
def test_run_asr_fallback_retry_passes_updated_model(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    _mock_reporter_class: MagicMock,
    _mock_processor_class: MagicMock,
    _mock_engine_func: MagicMock,
) -> None:
    mock_settings.ai_config = {
        "asr": {
            "fallback_model": "tiny",
            "default_model": "small",
        }
    }
    service = MagicMock()
    service.process.side_effect = ModelLoadError("out of memory")
    mock_service_class.return_value = service

    run_asr.request.retries = 0
    run_asr.request.max_retries = 3

    retry_mock = MagicMock()
    retry_mock.side_effect = Exception("retry scheduled")
    with patch.object(run_asr, "retry", retry_mock):
        try:
            run_asr.run(task_id="task-1", payload=_task_payload("large-v3"))
        except Exception as exc:
            if "retry scheduled" not in str(exc):
                raise

    retry_mock.assert_called_once()
    args = retry_mock.call_args.kwargs["args"]
    assert args[0] == "task-1"
    assert args[1]["model"] == "tiny"


@patch("celery_workers.tasks.asr_task._build_engine")
@patch("celery_workers.tasks.asr_task.AudioProcessor")
@patch("celery_workers.tasks.asr_task.GatewayProgressReporter")
@patch("celery_workers.tasks.asr_task.AsrService")
@patch("celery_workers.tasks.asr_task.settings")
def test_run_asr_fallback_exhausted_marks_failed(
    mock_settings: MagicMock,
    mock_service_class: MagicMock,
    _mock_reporter_class: MagicMock,
    _mock_processor_class: MagicMock,
    _mock_engine_func: MagicMock,
) -> None:
    mock_settings.ai_config = {
        "asr": {
            "fallback_model": "tiny",
            "default_model": "small",
        }
    }
    reporter = MagicMock()
    _mock_reporter_class.return_value = reporter

    service = MagicMock()
    service.process.side_effect = ModelLoadError("out of memory")
    mock_service_class.return_value = service

    run_asr.request.retries = 3
    run_asr.request.max_retries = 3

    try:
        run_asr.run(task_id="task-1", payload=_task_payload("large-v3"))
    except ModelLoadError:
        pass
    else:
        raise AssertionError("expected ModelLoadError to be raised")

    reporter.mark_status.assert_called_once_with(
        "task-1",
        "failed",
        error_message="out of memory",
    )

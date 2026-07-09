from __future__ import annotations

from unittest.mock import MagicMock, patch

from celery_workers.tasks.base import BaseAITask


class _DummyTask(BaseAITask):
    name = "dummy"


def _make_task() -> _DummyTask:
    return _DummyTask()


@patch("celery_workers.tasks.base.GatewayProgressReporter")
def test_on_retry_reports_running_with_attempt_count(mock_reporter_class: MagicMock) -> None:
    reporter = MagicMock()
    mock_reporter_class.return_value = reporter

    task = _make_task()
    with patch.object(task, "_attempt_count", return_value=3):
        task.on_retry(Exception("boom"), "task-1", [], {}, None)

    reporter.mark_status.assert_called_once_with(
        "task-1",
        "running",
        attempt_count=3,
    )


@patch("celery_workers.tasks.base.GatewayProgressReporter")
def test_on_failure_reports_failed_with_attempt_count(mock_reporter_class: MagicMock) -> None:
    reporter = MagicMock()
    mock_reporter_class.return_value = reporter

    task = _make_task()
    with patch.object(task, "_attempt_count", return_value=3):
        task.on_failure(Exception("boom"), "task-1", [], {}, None)

    reporter.mark_status.assert_called_once_with(
        "task-1",
        "failed",
        error_message="boom",
        attempt_count=3,
    )


@patch("celery_workers.tasks.base.GatewayProgressReporter")
def test_on_failure_skips_when_already_reported(mock_reporter_class: MagicMock) -> None:
    reporter = MagicMock()
    mock_reporter_class.return_value = reporter

    task = _make_task()
    task._failure_reported = True
    task.on_failure(Exception("boom"), "task-1", [], {}, None)

    reporter.mark_status.assert_not_called()


@patch("celery_workers.tasks.base.GatewayProgressReporter")
def test_on_success_reports_completed_with_result(mock_reporter_class: MagicMock) -> None:
    reporter = MagicMock()
    mock_reporter_class.return_value = reporter

    task = _make_task()
    with patch.object(task, "_attempt_count", return_value=2):
        task.on_success({"pages": []}, "task-1", [], {})

    reporter.mark_status.assert_called_once_with(
        "task-1",
        "completed",
        result={"pages": []},
        attempt_count=2,
    )

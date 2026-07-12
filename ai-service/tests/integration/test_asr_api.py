from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.fixture
def asr_app(app: Flask) -> Flask:
    return app


@pytest.fixture
def asr_client(asr_app: Flask) -> FlaskClient:
    return asr_app.test_client()


@patch("app.api.asr.run_asr")
def test_create_asr_task_success(
    mock_run_asr: MagicMock,
    asr_client: FlaskClient,
) -> None:
    mock_run_asr.delay.return_value = MagicMock(id="celery-task-1")
    response = asr_client.post(
        "/ai/v1/asr",
        headers={"X-Internal-Key": "test-internal-key"},
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "audio_url": "minio://resources/audio.mp3",
            "language": "zh",
            "model": "small",
        },
    )

    assert response.status_code == 202
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["task_id"] == "task-1"
    assert data["data"]["status"] == "pending"
    mock_run_asr.delay.assert_called_once()


@patch("app.api.asr.run_asr")
def test_create_asr_task_missing_internal_key(
    _mock_run_asr: MagicMock,
    asr_client: FlaskClient,
) -> None:
    response = asr_client.post(
        "/ai/v1/asr",
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "audio_url": "minio://resources/audio.mp3",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


@patch("app.api.asr.run_asr")
def test_create_asr_task_wrong_internal_key(
    _mock_run_asr: MagicMock,
    asr_client: FlaskClient,
) -> None:
    response = asr_client.post(
        "/ai/v1/asr",
        headers={"X-Internal-Key": "wrong-key"},
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "audio_url": "minio://resources/audio.mp3",
        },
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


@patch("app.api.asr.run_asr")
def test_create_asr_task_invalid_body(
    _mock_run_asr: MagicMock,
    asr_client: FlaskClient,
) -> None:
    response = asr_client.post(
        "/ai/v1/asr",
        headers={"X-Internal-Key": "test-internal-key"},
        json={"audio_url": "minio://resources/audio.mp3"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"

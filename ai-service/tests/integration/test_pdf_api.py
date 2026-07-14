from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.fixture
def pdf_app(app: Flask) -> Flask:
    return app


@pytest.fixture
def pdf_client(pdf_app: Flask) -> FlaskClient:
    return pdf_app.test_client()


@patch("app.api.pdf.run_pdf_parse")
def test_create_pdf_parse_task_success(
    mock_run_pdf_parse: MagicMock,
    pdf_client: FlaskClient,
) -> None:
    mock_run_pdf_parse.delay.return_value = MagicMock(id="celery-task-1")
    response = pdf_client.post(
        "/ai/v1/pdf/parse",
        headers={"X-Internal-Key": "test-internal-key"},
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "user_id": "user-1",
            "pdf_url": "minio://resources/doc.pdf",
        },
    )

    assert response.status_code == 202
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["task_id"] == "task-1"
    assert data["data"]["status"] == "pending"
    assert data["data"]["message"] == "PDF parse task queued"
    mock_run_pdf_parse.delay.assert_called_once()
    call_kwargs = mock_run_pdf_parse.delay.call_args.kwargs
    assert call_kwargs["task_id"] == "task-1"
    assert call_kwargs["payload"]["pdf_url"] == "minio://resources/doc.pdf"


@patch("app.api.pdf.run_pdf_parse")
def test_create_pdf_parse_task_missing_internal_key(
    _mock_run_pdf_parse: MagicMock,
    pdf_client: FlaskClient,
) -> None:
    response = pdf_client.post(
        "/ai/v1/pdf/parse",
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "pdf_url": "minio://resources/doc.pdf",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


@patch("app.api.pdf.run_pdf_parse")
def test_create_pdf_parse_task_wrong_internal_key(
    _mock_run_pdf_parse: MagicMock,
    pdf_client: FlaskClient,
) -> None:
    response = pdf_client.post(
        "/ai/v1/pdf/parse",
        headers={"X-Internal-Key": "wrong-key"},
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "pdf_url": "minio://resources/doc.pdf",
        },
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


@patch("app.api.pdf.run_pdf_parse")
def test_create_pdf_parse_task_invalid_body(
    _mock_run_pdf_parse: MagicMock,
    pdf_client: FlaskClient,
) -> None:
    response = pdf_client.post(
        "/ai/v1/pdf/parse",
        headers={"X-Internal-Key": "test-internal-key"},
        json={"pdf_url": "minio://resources/doc.pdf"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


@patch("app.api.pdf.run_pdf_parse")
def test_create_pdf_parse_task_unsupported_scheme(
    _mock_run_pdf_parse: MagicMock,
    pdf_client: FlaskClient,
) -> None:
    response = pdf_client.post(
        "/ai/v1/pdf/parse",
        headers={"X-Internal-Key": "test-internal-key"},
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "user_id": "user-1",
            "pdf_url": "https://example.com/doc.pdf",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "minio://" in data["error"]["message"]


@patch("app.api.pdf.run_pdf_parse")
def test_create_pdf_parse_task_missing_object_name(
    _mock_run_pdf_parse: MagicMock,
    pdf_client: FlaskClient,
) -> None:
    response = pdf_client.post(
        "/ai/v1/pdf/parse",
        headers={"X-Internal-Key": "test-internal-key"},
        json={
            "task_id": "task-1",
            "resource_id": "res-1",
            "user_id": "user-1",
            "pdf_url": "minio://resources",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"

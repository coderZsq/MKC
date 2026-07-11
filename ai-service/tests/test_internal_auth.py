import os

import pytest
from flask.testing import FlaskClient

INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "test-internal-key")


def test_internal_health_missing_key(client: FlaskClient) -> None:
    response = client.get("/api/v1/internal/health")
    assert response.status_code == 401

    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_internal_health_wrong_key(client: FlaskClient) -> None:
    response = client.get(
        "/api/v1/internal/health",
        headers={"X-Internal-Key": "wrong"},
    )
    assert response.status_code == 403

    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


def test_internal_health_valid_key(client: FlaskClient) -> None:
    response = client.get(
        "/api/v1/internal/health",
        headers={"X-Internal-Key": INTERNAL_API_KEY},
    )
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


def test_internal_health_empty_header_key_rejected(client: FlaskClient) -> None:
    response = client.get(
        "/api/v1/internal/health",
        headers={"X-Internal-Key": ""},
    )

    assert response.status_code == 403


def test_internal_health_empty_configured_key_rejects_empty_header(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.dependencies.settings.internal_api_key", "")

    response = client.get(
        "/api/v1/internal/health",
        headers={"X-Internal-Key": ""},
    )

    assert response.status_code == 403

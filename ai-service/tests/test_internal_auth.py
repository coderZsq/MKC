from flask.testing import FlaskClient


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
    assert response.status_code == 401


def test_internal_health_valid_key(client: FlaskClient) -> None:
    response = client.get(
        "/api/v1/internal/health",
        headers={"X-Internal-Key": "test-internal-key"},
    )
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"

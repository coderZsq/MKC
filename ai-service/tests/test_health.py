from flask.testing import FlaskClient


def test_health_returns_ok(client: FlaskClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"
    assert data["data"]["service"] == "ai-service"
    assert "dependencies" in data["data"]


def test_health_envelope_structure(client: FlaskClient) -> None:
    response = client.get("/api/v1/health")
    data = response.get_json()
    assert "success" in data
    assert "data" in data
    assert "error" in data
    assert "meta" in data


def test_not_found_returns_envelope(client: FlaskClient) -> None:
    response = client.get("/not-exist")
    assert response.status_code == 404

    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"

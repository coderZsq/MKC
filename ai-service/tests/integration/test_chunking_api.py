from __future__ import annotations

import pytest
from flask.testing import FlaskClient


class TestChunkingApi:
    def test_chunking_success(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/chunk",
            headers={"X-Internal-Key": "test-internal-key"},
            json={
                "resource_id": "res-1",
                "text": "第一段内容。\n\n第二段内容。",
                "metadata": {"page": 1},
                "strategy": "paragraph",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        chunks = data["data"]["chunks"]
        assert len(chunks) == 2
        assert chunks[0]["text"] == "第一段内容。"
        assert chunks[0]["metadata"] == {"page": 1}
        assert chunks[0]["resource_id"] == "res-1"

    def test_chunking_missing_internal_key(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/chunk",
            json={
                "resource_id": "res-1",
                "text": "一段内容。",
                "strategy": "paragraph",
            },
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_chunking_wrong_internal_key(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/chunk",
            headers={"X-Internal-Key": "wrong-key"},
            json={
                "resource_id": "res-1",
                "text": "一段内容。",
                "strategy": "paragraph",
            },
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "FORBIDDEN"

    def test_chunking_invalid_strategy(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/chunk",
            headers={"X-Internal-Key": "test-internal-key"},
            json={
                "resource_id": "res-1",
                "text": "一段内容。",
                "strategy": "not-a-strategy",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_STRATEGY"

    def test_chunking_text_too_long(
        self,
        client: FlaskClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("CHUNKING_MAX_INPUT_CHARS", "10")
        response = client.post(
            "/ai/v1/chunk",
            headers={"X-Internal-Key": "test-internal-key"},
            json={
                "resource_id": "res-1",
                "text": "a" * 11,
                "strategy": "paragraph",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "TEXT_TOO_LONG"

    def test_chunking_invalid_metadata(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/chunk",
            headers={"X-Internal-Key": "test-internal-key"},
            json={
                "resource_id": "res-1",
                "text": "一段内容。",
                "metadata": "not-a-dict",
                "strategy": "paragraph",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_chunking_empty_text(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/chunk",
            headers={"X-Internal-Key": "test-internal-key"},
            json={
                "resource_id": "res-1",
                "text": "",
                "strategy": "paragraph",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["chunks"] == []

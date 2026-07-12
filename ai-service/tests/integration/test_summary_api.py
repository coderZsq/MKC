from __future__ import annotations

import os

from flask.testing import FlaskClient

INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "test-internal-key")


def test_summarize_api_requires_internal_key(client: FlaskClient) -> None:
    response = client.post("/ai/v1/resources/res-1/summarize", json={"content": "正文"})

    assert response.status_code == 401


def test_summarize_api_returns_task_id(client: FlaskClient, monkeypatch) -> None:
    class FakeSummaryService:
        def generate(self, resource_id, payload):
            assert resource_id == "res-1"
            assert payload.content == "正文"
            return None

    monkeypatch.setitem(client.application.extensions, "summary_service", FakeSummaryService())

    response = client.post(
        "/ai/v1/resources/res-1/summarize",
        json={"content": "正文", "types": ["full"], "task_id": "task-1"},
        headers={"X-Internal-Key": INTERNAL_API_KEY},
    )

    assert response.status_code == 202
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["task_id"] == "task-1"

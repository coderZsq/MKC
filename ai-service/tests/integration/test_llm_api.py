from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.exceptions import LLMUnavailableError
from app.services.llm.models import LLMResponse, Usage

INTERNAL_KEY = os.environ["INTERNAL_API_KEY"]


@pytest.mark.integration
def test_llm_complete_success(client) -> None:
    response = client.post(
        "/ai/v1/llm/complete",
        json={"messages": [{"role": "user", "content": "hello"}]},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert "data" in body
    assert isinstance(body["data"]["content"], str)
    assert body["data"]["model"] == "glm-4-flash"


@pytest.mark.integration
def test_llm_complete_rejects_missing_key(client) -> None:
    response = client.post(
        "/ai/v1/llm/complete",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.integration
def test_llm_complete_rejects_invalid_key(client) -> None:
    response = client.post(
        "/ai/v1/llm/complete",
        json={"messages": [{"role": "user", "content": "hello"}]},
        headers={"X-Internal-Key": "wrong"},
    )

    assert response.status_code == 403
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.integration
def test_llm_complete_validates_request(client) -> None:
    response = client.post(
        "/ai/v1/llm/complete",
        json={"temperature": 1.5},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.integration
def test_llm_complete_returns_provider_error(client) -> None:
    with patch.object(
        client.application.extensions["llm"],
        "complete",
        side_effect=LLMUnavailableError("provider down"),
    ):
        response = client.post(
            "/ai/v1/llm/complete",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers={"X-Internal-Key": INTERNAL_KEY},
        )

    assert response.status_code == 503
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "LLM_UNAVAILABLE"


@pytest.mark.integration
def test_llm_complete_model_response_shape(client) -> None:
    fake_response = LLMResponse(
        content="shaped",
        model="glm-4-flash",
        finish_reason="stop",
        usage=Usage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
    )
    with patch.object(client.application.extensions["llm"], "complete", return_value=fake_response):
        response = client.post(
            "/ai/v1/llm/complete",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers={"X-Internal-Key": INTERNAL_KEY},
        )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["content"] == "shaped"
    assert data["finish_reason"] == "stop"
    assert data["usage"] == {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}

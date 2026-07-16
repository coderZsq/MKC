from __future__ import annotations

from typing import Any

from flask import Flask
from flask.testing import FlaskClient

from app.agent.tools.web_search_config import WebSearchConfig
from app.agent.tools.web_search_tool import WebSearchTool
from app.models.web_search import WebSearchRequest, WebSearchResult
from tests.unit.test_web_search_tool import _Provider

INTERNAL_API_KEY = "test-internal-key"


def test_web_search_endpoint_returns_results(app: Flask, client: FlaskClient) -> None:
    # MKC-TC-S4-8-012: internal test endpoint returns web search results.
    app.extensions["web_search_tool"] = WebSearchTool(
        provider=_Provider([WebSearchResult(title="T", url="https://example.com", snippet="S")]),
        config=WebSearchConfig(provider="mock"),
    )

    response = client.post(
        "/ai/v1/tools/web-search",
        json={"query": "query", "top_k": 1},
        headers={"X-Internal-Key": INTERNAL_API_KEY},
    )

    assert response.status_code == 200
    body: dict[str, Any] = response.get_json()
    assert body["data"]["source_type"] == "web"
    assert body["data"]["results"][0]["title"] == "T"


def test_web_search_endpoint_missing_internal_key_returns_401(client: FlaskClient) -> None:
    # MKC-TC-S4-8-013: missing X-Internal-Key is rejected.
    response = client.post("/ai/v1/tools/web-search", json={"query": "query"})

    assert response.status_code == 401


def test_web_search_endpoint_invalid_input_returns_400(client: FlaskClient) -> None:
    # MKC-TC-S4-8-022: invalid query is rejected by the test endpoint.
    response = client.post(
        "/ai/v1/tools/web-search",
        json={"query": "", "top_k": 1},
        headers={"X-Internal-Key": INTERNAL_API_KEY},
    )

    assert response.status_code == 400


def test_web_search_request_model_rejects_empty_query() -> None:
    # Keep the model validation path directly covered as well.
    try:
        WebSearchRequest(query="", top_k=1)
    except Exception as exc:
        assert "String should have at least 1 character" in str(exc)
    else:
        raise AssertionError("empty query should fail validation")

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from flask import Flask
from flask.testing import FlaskClient

from app.core.exceptions import RetrievalForbiddenError, RetrievalUnavailableError
from app.models.retrieval import RetrievalChunk, RetrievalResult
from app.services.retrieval.retrieval_service import RetrievalService

INTERNAL_API_KEY = "test-internal-key"


def _post(
    client: FlaskClient,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    merged_headers = {"X-Internal-Key": INTERNAL_API_KEY}
    if headers:
        merged_headers.update(headers)
    return client.post("/ai/v1/retrieve", headers=merged_headers, json=payload)


class TestRetrievalApi:
    def test_retrieve_returns_chunks_and_prompt(self, app: Flask, client: FlaskClient) -> None:
        from app import create_app

        retrieval_service = MagicMock(spec=RetrievalService)
        retrieval_service.retrieve.return_value = RetrievalResult(
            chunks=[
                RetrievalChunk(
                    chunk_id="c-1",
                    resource_id="res-1",
                    text="meeting topic",
                    score=0.89,
                    metadata={"page": 3},
                ),
            ],
            prompt="基于以下上下文...",
            context_token_count=12,
        )
        flask_app = create_app(retrieval_service=retrieval_service)
        flask_app.config.update({"TESTING": True})
        with flask_app.test_client() as c:
            response = _post(
                c,
                {
                    "question": "本次会议议题是什么？",
                    "user_id": "user-1",
                    "resource_ids": ["res-1"],
                },
            )

        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        chunks = body["data"]["chunks"]
        assert len(chunks) == 1
        assert chunks[0]["chunk_id"] == "c-1"
        assert chunks[0]["metadata"]["page"] == 3
        assert body["data"]["prompt"] == "基于以下上下文..."
        assert body["data"]["context_token_count"] == 12

    def test_retrieve_missing_question_returns_400(self, client: FlaskClient) -> None:
        response = _post(
            client,
            {
                "user_id": "user-1",
                "resource_ids": ["res-1"],
            },
        )
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_retrieve_empty_resource_ids_returns_400(self, client: FlaskClient) -> None:
        response = _post(
            client,
            {
                "question": "q",
                "user_id": "user-1",
                "resource_ids": [],
            },
        )
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_retrieve_missing_internal_key_returns_401(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/retrieve",
            json={
                "question": "q",
                "user_id": "user-1",
                "resource_ids": ["res-1"],
            },
        )
        assert response.status_code == 401
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_retrieve_vector_store_error_returns_503(self, app: Flask, client: FlaskClient) -> None:
        retrieval_service = MagicMock(spec=RetrievalService)
        retrieval_service.retrieve.side_effect = RetrievalUnavailableError("store down")
        app.extensions["retrieval"] = retrieval_service

        response = _post(
            client,
            {
                "question": "q",
                "user_id": "user-1",
                "resource_ids": ["res-1"],
            },
        )
        assert response.status_code == 503
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "RETRIEVAL_UNAVAILABLE"

    def test_retrieve_forbidden_resource_returns_403(self, app: Flask, client: FlaskClient) -> None:
        retrieval_service = MagicMock(spec=RetrievalService)
        retrieval_service.retrieve.side_effect = RetrievalForbiddenError("无权访问资源")
        app.extensions["retrieval"] = retrieval_service

        response = _post(
            client,
            {
                "question": "q",
                "user_id": "user-1",
                "resource_ids": ["res-1"],
            },
        )
        assert response.status_code == 403
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "FORBIDDEN"

    def test_retrieve_unexpected_error_returns_503(self, app: Flask, client: FlaskClient) -> None:
        retrieval_service = MagicMock(spec=RetrievalService)
        retrieval_service.retrieve.side_effect = RuntimeError("boom")
        app.extensions["retrieval"] = retrieval_service

        response = _post(
            client,
            {
                "question": "q",
                "user_id": "user-1",
                "resource_ids": ["res-1"],
            },
        )
        assert response.status_code == 503
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "RETRIEVAL_UNAVAILABLE"

    def test_create_app_accepts_injected_retrieval_service(self, app: Flask) -> None:
        assert "retrieval" in app.extensions
        assert isinstance(app.extensions["retrieval"], RetrievalService)

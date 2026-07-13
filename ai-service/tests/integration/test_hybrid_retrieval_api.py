from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from flask import Flask
from flask.testing import FlaskClient

from app.core.exceptions import RetrievalForbiddenError, RetrievalUnavailableError
from app.models.hybrid_retrieval import (
    FusionStats,
    HybridRetrievalResult,
    SearchResult,
)
from app.services.hybrid_retrieval.hybrid_retrieval_service import HybridRetrievalService

INTERNAL_API_KEY = "test-internal-key"


def _post(
    client: FlaskClient,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    merged = {"X-Internal-Key": INTERNAL_API_KEY}
    if headers:
        merged.update(headers)
    return client.post("/ai/v1/retrieve/hybrid", headers=merged, json=payload)


def _result(
    degraded: bool = False, chunks: list[SearchResult] | None = None
) -> HybridRetrievalResult:
    return HybridRetrievalResult(
        chunks=chunks
        or [
            SearchResult(
                chunk_id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text="会议讨论了路线图",
                score=0.92,
                source="rerank",
                metadata={"page": 1},
            ),
        ],
        fusion=FusionStats(bm25_count=3, vector_count=4, fused_count=6),
        degraded=degraded,
        elapsed_ms=42,
    )


def _stub_service(result: HybridRetrievalResult | None = None, side_effect=None) -> MagicMock:
    svc = MagicMock(spec=HybridRetrievalService)
    if side_effect is not None:
        svc.retrieve.side_effect = side_effect
    else:
        svc.retrieve.return_value = result if result is not None else _result()
    return svc


class TestHybridRetrievalApi:
    # MKC-TC-S4-7-001: happy path returns fused, reranked chunks.
    def test_hybrid_returns_chunks_and_fusion(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service()

        response = _post(
            client,
            {"question": "会议议题", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        chunks = body["data"]["chunks"]
        assert len(chunks) == 1
        assert chunks[0]["chunk_id"] == "c-1"
        assert chunks[0]["score"] == 0.92
        assert chunks[0]["source"] == "rerank"
        assert chunks[0]["metadata"]["page"] == 1
        assert body["data"]["fusion"] == {"bm25_count": 3, "vector_count": 4, "fused_count": 6}
        assert body["data"]["degraded"] is False
        assert body["data"]["elapsed_ms"] == 42

    # MKC-TC-S4-7-034: response never leaks user_id from chunks.
    def test_response_excludes_user_id(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service()

        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        body = response.get_json()
        assert "user_id" not in body["data"]["chunks"][0]

    # MKC-TC-S4-7-035: response follows the standard envelope contract.
    def test_response_envelope_contract(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service()

        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        body = response.get_json()
        assert set(body.keys()) >= {"success", "data", "error", "meta"}
        assert "timestamp" in body["meta"]

    # MKC-TC-S4-7-014: missing X-Internal-Key -> 401.
    def test_missing_internal_key_returns_401(self, client: FlaskClient) -> None:
        response = client.post(
            "/ai/v1/retrieve/hybrid",
            json={"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "UNAUTHORIZED"

    # MKC-TC-S4-7-019: wrong X-Internal-Key -> 403.
    def test_wrong_internal_key_returns_403(self, client: FlaskClient) -> None:
        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
            headers={"X-Internal-Key": "wrong"},
        )
        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    # MKC-TC-S4-7-015: missing question -> 400 INVALID_REQUEST.
    def test_missing_question_returns_400(self, client: FlaskClient) -> None:
        response = _post(
            client,
            {"user_id": "user-1", "resource_ids": ["res-1"]},
        )
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "INVALID_REQUEST"

    def test_empty_resource_ids_returns_400(self, client: FlaskClient) -> None:
        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": []},
        )
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "INVALID_REQUEST"

    def test_missing_user_id_returns_400(self, client: FlaskClient) -> None:
        response = _post(
            client,
            {"question": "q", "resource_ids": ["res-1"]},
        )
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "INVALID_REQUEST"

    # MKC-TC-S4-7-016 / 021: degradation is surfaced as degraded=true, still 200.
    def test_degraded_result_returns_200_with_flag(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service(result=_result(degraded=True))

        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["degraded"] is True

    # MKC-TC-S4-7-017: forbidden resource -> 403 FORBIDDEN.
    def test_forbidden_returns_403(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service(
            side_effect=RetrievalForbiddenError("无权访问资源"),
        )

        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    # MKC-TC-S4-7-020: retrieval unavailable -> 503.
    def test_unavailable_returns_503(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service(
            side_effect=RetrievalUnavailableError("两路均失败"),
        )

        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        assert response.status_code == 503
        assert response.get_json()["error"]["code"] == "RETRIEVAL_UNAVAILABLE"

    # MKC-TC-S4-7-026 (api-side): unexpected error -> 503 RETRIEVAL_UNAVAILABLE.
    def test_unexpected_error_returns_503(self, app: Flask, client: FlaskClient) -> None:
        app.extensions["hybrid_retrieval"] = _stub_service(side_effect=RuntimeError("boom"))

        response = _post(
            client,
            {"question": "q", "user_id": "user-1", "resource_ids": ["res-1"]},
        )

        assert response.status_code == 503
        assert response.get_json()["error"]["code"] == "RETRIEVAL_UNAVAILABLE"

    def test_create_app_builds_hybrid_extension(self, app: Flask) -> None:
        assert "hybrid_retrieval" in app.extensions
        assert isinstance(app.extensions["hybrid_retrieval"], HybridRetrievalService)

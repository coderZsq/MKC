from __future__ import annotations

from unittest.mock import MagicMock

from app.vector_store import ChromaStore

INTERNAL_API_KEY = "test-internal-key"


def _post(client, path: str, payload: dict, headers: dict | None = None):
    merged_headers = {"X-Internal-Key": INTERNAL_API_KEY}
    if headers:
        merged_headers.update(headers)
    return client.post(path, headers=merged_headers, json=payload)


class TestVectorsApi:
    def test_upsert_vectors_returns_count(self, client) -> None:
        response = _post(
            client,
            "/ai/v1/vectors/upsert",
            {
                "records": [
                    {
                        "id": "v1",
                        "resource_id": "res1",
                        "user_id": "u1",
                        "text": "hello world",
                        "vector": [1.0, 0.0, 0.0],
                        "metadata": {"title": "greeting"},
                    }
                ]
            },
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["data"]["upserted_count"] == 1

    def test_search_vectors_returns_results(self, client) -> None:
        _post(
            client,
            "/ai/v1/vectors/upsert",
            {
                "records": [
                    {
                        "id": "v1",
                        "resource_id": "res1",
                        "user_id": "u1",
                        "text": "hello world",
                        "vector": [1.0, 0.0, 0.0],
                    },
                    {
                        "id": "v2",
                        "resource_id": "res2",
                        "user_id": "u2",
                        "text": "goodbye",
                        "vector": [0.0, 1.0, 0.0],
                    },
                ]
            },
        )
        response = _post(
            client,
            "/ai/v1/vectors/search",
            {"vector": [1.0, 0.0, 0.0], "top_k": 2, "filters": {"resource_id": "res1"}},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        results = body["data"]["results"]
        assert len(results) == 1
        assert results[0]["id"] == "v1"
        assert results[0]["resource_id"] == "res1"

    def test_delete_vectors_returns_count(self, client) -> None:
        _post(
            client,
            "/ai/v1/vectors/upsert",
            {
                "records": [
                    {
                        "id": "v1",
                        "resource_id": "res1",
                        "user_id": "u1",
                        "text": "hello",
                        "vector": [1.0, 0.0, 0.0],
                    }
                ]
            },
        )
        response = _post(
            client,
            "/ai/v1/vectors/delete",
            {"resource_id": "res1", "user_id": "u1"},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["data"]["deleted_count"] == 1

    def test_upsert_empty_batch_returns_400(self, client) -> None:
        response = _post(client, "/ai/v1/vectors/upsert", {"records": []})
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "EMPTY_BATCH"

    def test_search_validation_error_returns_400(self, client) -> None:
        response = _post(client, "/ai/v1/vectors/search", {"vector": "not-a-list"})
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_missing_internal_key_returns_401(self, client) -> None:
        response = client.post(
            "/ai/v1/vectors/upsert",
            json={"records": [{"id": "v1", "resource_id": "r1", "vector": [1.0, 0.0, 0.0]}]},
        )
        assert response.status_code == 401
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_vector_store_error_returns_500(self, app, client) -> None:
        mock_store = MagicMock(spec=ChromaStore)
        mock_store.upsert.side_effect = RuntimeError("boom")
        app.extensions["vector_store"] = mock_store
        response = _post(
            client,
            "/ai/v1/vectors/upsert",
            {
                "records": [
                    {
                        "id": "v1",
                        "resource_id": "res1",
                        "vector": [1.0, 0.0, 0.0],
                    }
                ]
            },
        )
        assert response.status_code == 500
        body = response.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "VECTOR_STORE_ERROR"

    def test_create_app_accepts_injected_vector_store(self, vector_store) -> None:
        from app import create_app

        app = create_app(vector_store=vector_store)
        assert app.extensions["vector_store"] is vector_store

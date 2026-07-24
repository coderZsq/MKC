from __future__ import annotations

from app.models.retrieval import RetrievalRequest, RetrievalResult
from app.services.llamaindex.query_engine import LlamaIndexQueryEngine


class _FakeRetrievalEngine:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.requests: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self.requests.append(request)
        return self.result


def test_query_engine_delegates_to_retrieval_engine_without_answer_generation() -> None:
    result = RetrievalResult(chunks=[], prompt="prompt", context_token_count=0)
    retrieval_engine = _FakeRetrievalEngine(result)
    query_engine = LlamaIndexQueryEngine(retrieval_engine)  # type: ignore[arg-type]
    request = RetrievalRequest(
        question="question",
        user_id="user-1",
        resource_ids=["res-1"],
    )

    actual = query_engine.query(request)

    assert actual is result
    assert retrieval_engine.requests == [request]

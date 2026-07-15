from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import RetrievalForbiddenError, RetrievalUnavailableError
from app.models.retrieval import RetrievalRequest
from app.models.vector_record import VectorSearchResult
from app.services.chunking.token_estimator import TokenEstimator
from app.services.retrieval.prompt_builder import PromptBuilder
from app.services.retrieval.retrieval_service import RetrievalConfig, RetrievalService


@pytest.fixture
def retrieval_config() -> RetrievalConfig:
    return RetrievalConfig(
        default_top_k=5,
        score_threshold=0.7,
        max_context_tokens=4096,
        prompt_template="prompts/rag.txt",
    )


@pytest.fixture
def prompt_builder() -> PromptBuilder:
    return PromptBuilder(template_text="chunks:{{ chunks|length }} question:{{ question }}")


@pytest.fixture
def token_estimator() -> TokenEstimator:
    return TokenEstimator()


@pytest.fixture
def mock_embedding_svc() -> MagicMock:
    service = MagicMock()
    service.embed_query.return_value = [0.1] * 8
    return service


@pytest.fixture
def mock_vector_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def retrieval_service(
    mock_embedding_svc: MagicMock,
    mock_vector_store: MagicMock,
    prompt_builder: PromptBuilder,
    retrieval_config: RetrievalConfig,
    token_estimator: TokenEstimator,
) -> RetrievalService:
    return RetrievalService(
        embedding_svc=mock_embedding_svc,
        vector_store=mock_vector_store,
        prompt_builder=prompt_builder,
        config=retrieval_config,
        token_estimator=token_estimator,
    )


class TestRetrievalService:
    def test_retrieve_generates_query_embedding_and_searches(
        self,
        retrieval_service: RetrievalService,
        mock_embedding_svc: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text="relevant text",
                metadata={"page": 1},
                score=0.9,
            ),
        ]
        request = RetrievalRequest(
            question="what is the topic?",
            user_id="user-1",
            resource_ids=["res-1"],
        )

        result = retrieval_service.retrieve(request)

        mock_embedding_svc.embed_query.assert_called_once_with("what is the topic?")
        mock_vector_store.search.assert_called_once_with(
            vector=[0.1] * 8,
            top_k=5,
            filters={"user_id": "user-1", "resource_ids": ["res-1"]},
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "c-1"
        assert result.chunks[0].score == 0.9

    def test_retrieve_filters_by_resource_ids(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = []
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1", "res-2"],
        )

        retrieval_service.retrieve(request)

        first_search = mock_vector_store.search.call_args_list[0]
        assert first_search.kwargs["filters"]["resource_ids"] == [
            "res-1",
            "res-2",
        ]
        assert first_search.kwargs["top_k"] > request.top_k

    def test_retrieve_single_resource_keeps_requested_top_k(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = []
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
            top_k=5,
        )

        retrieval_service.retrieve(request)

        assert mock_vector_store.search.call_args[1]["top_k"] == 5

    def test_retrieve_filters_by_score_threshold(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text="high score",
                metadata={},
                score=0.9,
            ),
            VectorSearchResult(
                id="c-2",
                resource_id="res-1",
                user_id="user-1",
                text="low score",
                metadata={},
                score=0.5,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
            score_threshold=0.7,
        )

        result = retrieval_service.retrieve(request)

        assert [chunk.chunk_id for chunk in result.chunks] == ["c-1"]

    def test_retrieve_compresses_context_by_token_budget(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        long_text = "word " * 1000
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text=long_text,
                metadata={},
                score=0.95,
            ),
            VectorSearchResult(
                id="c-2",
                resource_id="res-1",
                user_id="user-1",
                text="second chunk",
                metadata={},
                score=0.85,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
            max_context_tokens=50,
        )

        result = retrieval_service.retrieve(request)

        assert [chunk.chunk_id for chunk in result.chunks] == ["c-1"]
        assert result.context_token_count > 0

    def test_retrieve_sorts_by_score_descending(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-low",
                resource_id="res-1",
                user_id="user-1",
                text="text",
                metadata={},
                score=0.7,
            ),
            VectorSearchResult(
                id="c-high",
                resource_id="res-1",
                user_id="user-1",
                text="text",
                metadata={},
                score=0.95,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
        )

        result = retrieval_service.retrieve(request)

        assert [chunk.chunk_id for chunk in result.chunks] == ["c-high", "c-low"]

    def test_retrieve_deduplicates_repeated_library_chunks(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        duplicate_text = "每个人的龙场悟道 王阳明在龙场完成思想突破"
        global_hits = [
            VectorSearchResult(
                id=f"pdf-{index}",
                resource_id=f"pdf-res-{index}",
                user_id="user-1",
                text=duplicate_text,
                metadata={"source_type": "pdf"},
                score=0.95 - index * 0.01,
            )
            for index in range(5)
        ]
        audio_hit = VectorSearchResult(
            id="audio-1",
            resource_id="audio-res",
            user_id="user-1",
            text="音频里讲龙场悟道包含生死考验和道德觉悟",
            metadata={"source_type": "audio", "start_time": 10.0},
            score=0.82,
        )

        def _search_side_effect(*_args: object, **kwargs: object) -> list[VectorSearchResult]:
            filters = kwargs["filters"]
            assert isinstance(filters, dict)
            resource_ids = filters["resource_ids"]
            if resource_ids == ["audio-res"]:
                return [audio_hit]
            if isinstance(resource_ids, list) and len(resource_ids) == 1:
                return []
            return global_hits

        mock_vector_store.search.side_effect = _search_side_effect
        request = RetrievalRequest(
            question="龙场悟道是什么",
            user_id="user-1",
            resource_ids=[
                "pdf-res-0",
                "pdf-res-1",
                "pdf-res-2",
                "pdf-res-3",
                "pdf-res-4",
                "audio-res",
            ],
            top_k=5,
            score_threshold=0.7,
        )

        result = retrieval_service.retrieve(request)

        assert [chunk.chunk_id for chunk in result.chunks] == ["pdf-0", "audio-1"]
        assert mock_vector_store.search.call_count == 7

    def test_retrieve_returns_chunk_metadata(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text="text",
                metadata={"page": 3, "timestamp_start": 120.0},
                score=0.9,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
        )

        result = retrieval_service.retrieve(request)

        chunk = result.chunks[0]
        assert chunk.metadata == {"page": 3, "timestamp_start": 120.0}
        assert chunk.resource_id == "res-1"
        assert chunk.score == 0.9

    def test_retrieve_empty_results_returns_no_knowledge_prompt(
        self,
        mock_embedding_svc: MagicMock,
        mock_vector_store: MagicMock,
        token_estimator: TokenEstimator,
        retrieval_config: RetrievalConfig,
    ) -> None:
        mock_vector_store.search.return_value = []
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
        )
        service = RetrievalService(
            embedding_svc=mock_embedding_svc,
            vector_store=mock_vector_store,
            prompt_builder=PromptBuilder(),
            config=retrieval_config,
            token_estimator=token_estimator,
        )

        result = service.retrieve(request)

        assert result.chunks == []
        assert "无相关知识" in result.prompt
        assert result.context_token_count == 0

    def test_retrieve_store_failure_raises_unavailable(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.side_effect = RuntimeError("store down")
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
        )

        with pytest.raises(RetrievalUnavailableError) as exc_info:
            retrieval_service.retrieve(request)

        assert exc_info.value.code == "RETRIEVAL_UNAVAILABLE"

    def test_retrieve_unauthorized_chunk_raises_forbidden(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="other-res",
                user_id="user-1",
                text="text",
                metadata={},
                score=0.9,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
        )

        with pytest.raises(RetrievalForbiddenError) as exc_info:
            retrieval_service.retrieve(request)

        assert exc_info.value.code == "FORBIDDEN"

    def test_retrieve_single_chunk_exceeding_budget_keeps_highest(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        long_text = "word " * 1000
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text=long_text,
                metadata={},
                score=0.9,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
            max_context_tokens=10,
        )

        result = retrieval_service.retrieve(request)

        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == "c-1"
        assert result.context_token_count > 10

    def test_retrieve_various_metadata_preserved(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search.return_value = [
            VectorSearchResult(
                id="c-1",
                resource_id="res-1",
                user_id="user-1",
                text="text",
                metadata={"key": "value", "number": 42},
                score=0.9,
            ),
        ]
        request = RetrievalRequest(
            question="question",
            user_id="user-1",
            resource_ids=["res-1"],
        )

        result = retrieval_service.retrieve(request)

        assert result.chunks[0].metadata == {"key": "value", "number": 42}

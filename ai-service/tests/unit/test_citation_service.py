from app.models.retrieval import RetrievalChunk
from app.services.citation_formatter import CitationFormatter
from app.services.citation_service import CitationService, citation_to_event_data
from app.services.citation_validator import CitationValidator


def test_service_builds_validated_citations() -> None:
    service = CitationService(CitationFormatter(), CitationValidator(log_dropped=False))
    chunks = [
        RetrievalChunk(
            chunk_id="c-1",
            resource_id="res-1",
            text="source",
            score=0.88,
            metadata={"page": 5, "resource_type": "pdf"},
        )
    ]

    result = service.build_citations("Answer [^1].", chunks, {"res-1"})

    assert result.answer == "Answer [^1]."
    assert len(result.citations) == 1
    assert citation_to_event_data(result.citations[0]) == {
        "index": 1,
        "chunk_id": "c-1",
        "resource_id": "res-1",
        "resource_type": "pdf",
        "page": 5,
        "score": 0.88,
        "snippet": "source",
    }


def test_service_returns_empty_citations_without_markers() -> None:
    service = CitationService(CitationFormatter(), CitationValidator(log_dropped=False))
    chunk = RetrievalChunk(
        chunk_id="c-1",
        resource_id="res-1",
        text="source",
        score=0.88,
        metadata={},
    )

    result = service.build_citations("Answer without markers.", [chunk], {"res-1"})

    assert result.citations == []


def test_service_allows_citations_when_authorized_scope_is_empty() -> None:
    service = CitationService(CitationFormatter(), CitationValidator(log_dropped=False))
    chunk = RetrievalChunk(
        chunk_id="c-1",
        resource_id="res-1",
        text="source",
        score=0.88,
        metadata={},
    )

    result = service.build_citations("Answer [^1].", [chunk], set())

    assert len(result.citations) == 1
    assert result.citations[0].resource_id == "res-1"

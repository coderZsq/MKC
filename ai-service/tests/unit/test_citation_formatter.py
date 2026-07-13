from app.models.retrieval import RetrievalChunk
from app.services.citation_formatter import CitationFormatter
from app.services.citation_service import format_timestamp


def test_formatter_maps_markers_to_chunk_metadata() -> None:
    formatter = CitationFormatter(snippet_max_chars=12)
    chunks = [
        RetrievalChunk(
            chunk_id="c-1",
            resource_id="res-a",
            text="PDF source snippet is long",
            score=0.91,
            metadata={"resource_type": "pdf", "page": "3"},
        ),
        RetrievalChunk(
            chunk_id="c-2",
            resource_id="res-b",
            text="audio source snippet",
            score=0.82,
            metadata={
                "resource_type": "audio",
                "timestamp_start": 120.5,
                "timestamp_end": "145",
            },
        ),
    ]

    result = formatter.format("Answer [^1] and audio [^2].", chunks)

    assert [c.index for c in result.citations] == [1, 2]
    assert result.citations[0].chunk_id == "c-1"
    assert result.citations[0].resource_id == "res-a"
    assert result.citations[0].page == 3
    assert result.citations[0].snippet == "PDF source s"
    assert result.citations[1].resource_type == "audio"
    assert result.citations[1].timestamp_start == 120.5
    assert result.citations[1].timestamp_end == 145.0


def test_formatter_reuses_duplicate_markers_and_drops_out_of_range() -> None:
    formatter = CitationFormatter()
    chunks = [
        RetrievalChunk(
            chunk_id="c-1",
            resource_id="res-a",
            text="text",
            score=0.91,
            metadata={},
        )
    ]

    result = formatter.format("Repeat [^1], again [^1], invalid [^3].", chunks)

    assert len(result.citations) == 1
    assert result.citations[0].index == 1


def test_formatter_degrades_when_metadata_missing() -> None:
    formatter = CitationFormatter()
    chunk = RetrievalChunk(
        chunk_id="c-1",
        resource_id="res-a",
        text="text",
        score=0.7,
        metadata={},
    )

    result = formatter.format("Answer [^1].", [chunk])

    assert result.citations[0].resource_type == "pdf"
    assert result.citations[0].page is None
    assert result.citations[0].timestamp_start is None


def test_format_timestamp_outputs_mm_ss() -> None:
    assert format_timestamp(75.8) == "01:15"

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


def test_formatter_renumbers_skipped_markers_contiguously() -> None:
    formatter = CitationFormatter()
    chunks = [
        RetrievalChunk(
            chunk_id="c-1",
            resource_id="res-a",
            text="first",
            score=0.91,
            metadata={},
        ),
        RetrievalChunk(
            chunk_id="c-2",
            resource_id="res-b",
            text="second",
            score=0.82,
            metadata={},
        ),
        RetrievalChunk(
            chunk_id="c-3",
            resource_id="res-c",
            text="third",
            score=0.73,
            metadata={},
        ),
    ]

    result = formatter.format("Answer cites second [^2] and third [^3].", chunks)

    assert result.answer == "Answer cites second [^1] and third [^2]."
    assert [c.index for c in result.citations] == [1, 2]
    assert [c.original_index for c in result.citations] == [2, 3]
    assert [c.chunk_id for c in result.citations] == ["c-2", "c-3"]


def test_formatter_maps_audio_source_type_and_time_metadata() -> None:
    formatter = CitationFormatter()
    chunk = RetrievalChunk(
        chunk_id="audio-c-1",
        resource_id="audio-res",
        text="audio transcript",
        score=0.88,
        metadata={
            "source_type": "audio",
            "start_time": 10.5,
            "end_time": "18.25",
        },
    )

    result = formatter.format("Audio answer [^1].", [chunk])

    assert result.citations[0].resource_type == "audio"
    assert result.citations[0].timestamp_start == 10.5
    assert result.citations[0].timestamp_end == 18.25


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

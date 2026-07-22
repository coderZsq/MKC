from __future__ import annotations

from llama_index.core.schema import NodeWithScore, TextNode

from app.models.vector_record import VectorRecord, VectorSearchResult
from app.services.citation_formatter import CitationFormatter
from app.services.llamaindex.metadata_mapper import (
    node_to_retrieval_chunk,
    node_with_score_to_chunk,
    vector_record_to_node,
    vector_search_result_to_node,
)


def test_vector_record_to_text_node_preserves_metadata() -> None:
    record = VectorRecord(
        id="chunk-1",
        resource_id="res-1",
        user_id="user-1",
        text="hello node",
        vector=[0.1, 0.2],
        metadata={
            "page": 3,
            "start_sec": 12.5,
            "end_sec": 18.0,
            "source_type": "audio",
        },
    )

    node = vector_record_to_node(record)

    assert isinstance(node, TextNode)
    assert node.node_id == "chunk-1"
    assert node.get_content() == "hello node"
    assert node.metadata["chunk_id"] == "chunk-1"
    assert node.metadata["resource_id"] == "res-1"
    assert node.metadata["user_id"] == "user-1"
    assert node.metadata["page"] == 3
    assert node.metadata["start_sec"] == 12.5
    assert node.metadata["timestamp_start"] == 12.5
    assert node.metadata["end_sec"] == 18.0
    assert node.metadata["timestamp_end"] == 18.0
    assert node.metadata["source_type"] == "audio"
    assert node.metadata["resource_type"] == "audio"


def test_node_with_score_to_retrieval_chunk_preserves_fields() -> None:
    node = TextNode(
        id_="node-1",
        text="retrieved text",
        metadata={
            "chunk_id": "chunk-1",
            "resource_id": "res-1",
            "user_id": "user-1",
            "page": "4",
            "timestamp_start": 2.5,
            "timestamp_end": 8.0,
            "source_type": "audio",
        },
    )

    chunk = node_with_score_to_chunk(NodeWithScore(node=node, score=0.87))

    assert chunk.chunk_id == "chunk-1"
    assert chunk.resource_id == "res-1"
    assert chunk.text == "retrieved text"
    assert chunk.score == 0.87
    assert chunk.metadata["user_id"] == "user-1"
    assert chunk.metadata["page"] == "4"
    assert chunk.metadata["timestamp_start"] == 2.5
    assert chunk.metadata["timestamp_end"] == 8.0
    assert chunk.metadata["start_sec"] == 2.5
    assert chunk.metadata["end_sec"] == 8.0


def test_citation_metadata_survives_round_trip() -> None:
    record = VectorRecord(
        id="audio-chunk",
        resource_id="audio-res",
        user_id="user-1",
        text="audio transcript",
        vector=[0.1],
        metadata={
            "page": 9,
            "start_sec": 120.5,
            "end_sec": 145.0,
            "source_type": "audio",
        },
    )

    chunk = node_to_retrieval_chunk(vector_record_to_node(record), score=0.91)
    citation = CitationFormatter().format("Answer [^1].", [chunk]).citations[0]

    assert chunk.metadata["resource_id"] == "audio-res"
    assert chunk.metadata["user_id"] == "user-1"
    assert chunk.metadata["chunk_id"] == "audio-chunk"
    assert citation.chunk_id == "audio-chunk"
    assert citation.resource_id == "audio-res"
    assert citation.resource_type == "audio"
    assert citation.page == 9
    assert citation.timestamp_start == 120.5
    assert citation.timestamp_end == 145.0


def test_empty_text_and_missing_optional_metadata_degrade_safely() -> None:
    record = VectorRecord(
        id="empty-chunk",
        resource_id="res-1",
        user_id="user-1",
        text="",
        vector=[0.1],
        metadata={},
    )

    chunk = node_to_retrieval_chunk(vector_record_to_node(record))

    assert chunk.chunk_id == "empty-chunk"
    assert chunk.resource_id == "res-1"
    assert chunk.text == ""
    assert chunk.score == 0.0
    assert chunk.metadata["user_id"] == "user-1"
    assert "page" not in chunk.metadata


def test_node_with_missing_score_defaults_to_zero() -> None:
    node = TextNode(id_="node-1", text="text", metadata={"resource_id": "res-1"})

    chunk = node_with_score_to_chunk(NodeWithScore(node=node, score=None))

    assert chunk.chunk_id == "node-1"
    assert chunk.resource_id == "res-1"
    assert chunk.score == 0.0


def test_vector_search_result_to_node_keeps_score_in_metadata() -> None:
    result = VectorSearchResult(
        id="chunk-1",
        resource_id="res-1",
        user_id="user-1",
        text="search hit",
        metadata={"resource_type": "pdf"},
        score=0.76,
    )

    chunk = node_to_retrieval_chunk(vector_search_result_to_node(result))

    assert chunk.chunk_id == "chunk-1"
    assert chunk.resource_id == "res-1"
    assert chunk.text == "search hit"
    assert chunk.score == 0.76
    assert chunk.metadata["resource_type"] == "pdf"

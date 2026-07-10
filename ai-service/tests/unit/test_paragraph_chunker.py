from __future__ import annotations

import pytest

from app.services.chunking.config import ChunkingConfig
from app.services.chunking.paragraph_chunker import ParagraphChunker


@pytest.fixture
def chunk_config() -> ChunkingConfig:
    return ChunkingConfig(chunk_size=100, chunk_overlap=10)


@pytest.fixture
def chunker(chunk_config: ChunkingConfig) -> ParagraphChunker:
    return ParagraphChunker(chunk_config)


def test_paragraph_chunker_empty_text(chunker: ParagraphChunker) -> None:
    assert chunker.split("", "res-1", {}) == []


def test_paragraph_chunker_splits_by_blank_lines(
    chunker: ParagraphChunker,
) -> None:
    text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
    chunks = chunker.split(text, "res-1", {"page": 1})

    assert len(chunks) == 3
    assert chunks[0].text == "第一段内容。"
    assert chunks[1].text == "第二段内容。"
    assert chunks[2].text == "第三段内容。"
    assert chunks[0].index == 0
    assert chunks[2].index == 2
    assert all(chunk.metadata == {"page": 1} for chunk in chunks)


def test_paragraph_chunker_preserves_positions(chunker: ParagraphChunker) -> None:
    text = "第一段内容。\n\n第二段内容。"
    chunks = chunker.split(text, "res-1", {})

    assert chunks[0].start_pos == 0
    assert chunks[0].end_pos == text.find("\n\n")
    assert chunks[1].start_pos == text.find("第二段")
    assert chunks[1].end_pos == len(text)


def test_paragraph_chunker_splits_long_paragraph() -> None:
    config = ChunkingConfig(chunk_size=20, chunk_overlap=5)
    chunker = ParagraphChunker(config)

    sentences = ["句子一。", "句子二。", "句子三。", "句子四。", "句子五。"]
    text = "".join(sentences)
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) >= 2
    combined = "".join(chunk.text for chunk in chunks)
    assert combined == text
    for chunk in chunks:
        assert chunk.token_count <= config.chunk_size
        assert len(chunk.text) <= config.chunk_size


def test_paragraph_chunker_resource_id(chunker: ParagraphChunker) -> None:
    chunks = chunker.split("一段内容。", "resource-abc", {})
    assert len(chunks) == 1
    assert chunks[0].resource_id == "resource-abc"
    assert chunks[0].id == "resource-abc-0"


def test_paragraph_chunker_does_not_overlap_across_paragraphs() -> None:
    config = ChunkingConfig(chunk_size=100, chunk_overlap=50)
    chunker = ParagraphChunker(config)
    text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) == 3
    for i in range(1, len(chunks)):
        assert chunks[i].start_pos >= chunks[i - 1].end_pos

from __future__ import annotations

import pytest

from app.services.chunking.config import ChunkingConfig
from app.services.chunking.semantic_chunker import SemanticChunker


@pytest.fixture
def chunk_config() -> ChunkingConfig:
    return ChunkingConfig(chunk_size=20, chunk_overlap=10)


@pytest.fixture
def chunker(chunk_config: ChunkingConfig) -> SemanticChunker:
    return SemanticChunker(chunk_config)


def test_semantic_chunker_empty_text(chunker: SemanticChunker) -> None:
    assert chunker.split("", "res-1", {}) == []


def test_semantic_chunker_preserves_heading_boundaries(chunker: SemanticChunker) -> None:
    text = "# 第一章\n第一章的内容。\n\n# 第二章\n第二章的内容。"
    chunks = chunker.split(text, "res-1", {"page": 1})

    assert len(chunks) >= 2
    heading_chunks = [chunk for chunk in chunks if "#" in chunk.text]
    assert len(heading_chunks) >= 2
    for chunk in chunks:
        assert chunk.metadata == {"page": 1}


def test_semantic_chunker_does_not_split_heading(chunker: SemanticChunker) -> None:
    text = "# 这是一个标题\n正文内容在这里。"
    chunks = chunker.split(text, "res-1", {})

    heading_part = chunks[0].text
    assert "#" in heading_part


def test_semantic_chunker_splits_long_section() -> None:
    config = ChunkingConfig(chunk_size=20, chunk_overlap=5)
    chunker = SemanticChunker(config)
    text = "# 标题\n" + "这是正文。" * 10
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) >= 2
    combined = "".join(chunk.text for chunk in chunks)
    assert combined == text
    for chunk in chunks:
        assert chunk.token_count <= config.chunk_size


def test_semantic_chunker_positions_are_ordered(chunker: SemanticChunker) -> None:
    text = "# A\n内容。\n\n# B\n更多内容。"
    chunks = chunker.split(text, "res-1", {})

    for i in range(1, len(chunks)):
        assert chunks[i].start_pos >= chunks[i - 1].start_pos
        assert chunks[i].end_pos > chunks[i].start_pos


def test_semantic_chunker_uses_custom_separators() -> None:
    config = ChunkingConfig(
        chunk_size=10,
        chunk_overlap=0,
        separators=["---", "\n", "", ""],
    )
    chunker = SemanticChunker(config)
    text = "第一部分---第二部分---第三部分"
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) == 3
    assert chunks[0].text == "第一部分"
    assert chunks[1].text == "---第二部分"
    assert chunks[2].text == "---第三部分"


def test_semantic_chunker_does_not_overlap_across_boundaries() -> None:
    config = ChunkingConfig(chunk_size=20, chunk_overlap=10)
    chunker = SemanticChunker(config)
    text = "# 标题\n" + "这是正文。" * 10
    chunks = chunker.split(text, "res-1", {})

    combined = "".join(chunk.text for chunk in chunks)
    assert combined == text
    for i in range(1, len(chunks)):
        assert chunks[i].start_pos >= chunks[i - 1].end_pos

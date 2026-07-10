from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.chunking.config import ChunkingConfig
from app.services.chunking.fixed_token_chunker import FixedTokenChunker
from app.services.chunking.token_estimator import TokenEstimator


@pytest.fixture
def chunk_config() -> ChunkingConfig:
    return ChunkingConfig(chunk_size=50, chunk_overlap=10)


@pytest.fixture
def chunker(chunk_config: ChunkingConfig) -> FixedTokenChunker:
    return FixedTokenChunker(chunk_config)


def test_fixed_token_chunker_empty_text(chunker: FixedTokenChunker) -> None:
    assert chunker.split("", "res-1", {}) == []


def test_fixed_token_chunker_limits_chunk_size(
    chunker: FixedTokenChunker,
    chunk_config: ChunkingConfig,
) -> None:
    text = "word " * 200
    chunks = chunker.split(text, "res-1", {"page": 2})

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.token_count <= chunk_config.chunk_size
        assert chunk.metadata == {"page": 2}


def test_fixed_token_chunker_overlap(chunk_config: ChunkingConfig) -> None:
    chunker = FixedTokenChunker(chunk_config)
    text = "token " * 120
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) >= 2
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        curr = chunks[i]
        assert curr.start_pos < prev.end_pos
        assert curr.start_pos > prev.start_pos
        step_tokens = chunker.estimator.count(text[prev.start_pos : curr.start_pos])
        assert step_tokens < chunk_config.chunk_size


def test_fixed_token_chunker_covers_full_text(chunker: FixedTokenChunker) -> None:
    text = "This is a sample sentence used for fixed token chunking. " * 10
    chunks = chunker.split(text, "res-1", {})

    assert chunks[0].start_pos == 0
    assert chunks[-1].end_pos == len(text)
    for chunk in chunks:
        assert text.find(chunk.text) != -1


def test_fixed_token_chunker_fallback_when_tiktoken_fails() -> None:
    config = ChunkingConfig(chunk_size=20, chunk_overlap=5)
    with patch("tiktoken.get_encoding", side_effect=RuntimeError("no encoding")):
        estimator = TokenEstimator()
        chunker = FixedTokenChunker(config, estimator=estimator)
        text = "a" * 100
        chunks = chunker.split(text, "res-1", {})

    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.text) <= config.chunk_size


def test_fixed_token_chunker_chinese_text(
    chunk_config: ChunkingConfig,
) -> None:
    chunker = FixedTokenChunker(chunk_config)
    text = "中文文本也可以被正确分块。" * 30
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.token_count <= chunk_config.chunk_size
        assert text.find(chunk.text) != -1


def test_fixed_token_chunker_long_text_without_separators(
    chunker: FixedTokenChunker,
    chunk_config: ChunkingConfig,
) -> None:
    text = "a" * 1000
    chunks = chunker.split(text, "res-1", {})

    assert len(chunks) >= 2
    assert chunks[0].start_pos == 0
    assert chunks[-1].end_pos == len(text)
    for chunk in chunks:
        assert chunk.token_count <= chunk_config.chunk_size

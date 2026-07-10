from __future__ import annotations

import pytest

from app.models.chunk import Chunk
from app.services.chunking.base_chunker import BaseChunker
from app.services.chunking.config import ChunkingConfig


class _ConcreteChunker(BaseChunker):
    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]:
        return []


@pytest.fixture
def chunker() -> BaseChunker:
    return _ConcreteChunker(ChunkingConfig(chunk_size=10, chunk_overlap=0))


class TestBaseChunker:
    def test_size_exceeded_by_character_length(self, chunker: BaseChunker) -> None:
        assert chunker._size_exceeded("a" * 11) is True

    def test_size_exceeded_within_limit(self, chunker: BaseChunker) -> None:
        assert chunker._size_exceeded("short") is False

    def test_split_chars_respects_chunk_size(self, chunker: BaseChunker) -> None:
        pieces = chunker._split_chars("a" * 25, 0)
        assert len(pieces) == 3
        assert pieces[0] == ("a" * 10, 0, 10)
        assert pieces[1] == ("a" * 10, 10, 20)
        assert pieces[2] == ("a" * 5, 20, 25)

    def test_split_text_empty_returns_empty(self, chunker: BaseChunker) -> None:
        assert chunker._split_text("", 0, ["\n", ""], merge_across=True) == []

    def test_split_text_fits_without_splitting(self, chunker: BaseChunker) -> None:
        assert chunker._split_text("small", 0, ["\n", ""], merge_across=True) == [
            ("small", 0, 5),
        ]

    def test_split_text_leading_separator_skipped(self, chunker: BaseChunker) -> None:
        pieces = chunker._split_text("\nhello\nworld", 0, ["\n", ""], merge_across=True)
        assert len(pieces) == 2
        assert pieces[0] == ("\nhello", 0, 6)
        assert pieces[1] == ("\nworld", 6, 12)

    def test_split_text_empty_separator_fallback(self, chunker: BaseChunker) -> None:
        pieces = chunker._split_text("a" * 25, 5, [""], merge_across=True)
        assert len(pieces) == 3
        assert pieces[0][1] == 5
        assert pieces[-1][2] == 30

    def test_merge_pieces_empty_returns_empty(self, chunker: BaseChunker) -> None:
        assert chunker._merge_pieces([]) == []

    def test_merge_pieces_combines_when_fits(self, chunker: BaseChunker) -> None:
        pieces = [("abc", 0, 3), ("def", 3, 6)]
        merged = chunker._merge_pieces(pieces)
        assert merged == [("abcdef", 0, 6)]

    def test_merge_pieces_keeps_separate_when_too_large(self, chunker: BaseChunker) -> None:
        pieces = [("a" * 10, 0, 10), ("b" * 10, 10, 20)]
        merged = chunker._merge_pieces(pieces)
        assert merged == pieces

    def test_merge_pieces_partial_merge(self, chunker: BaseChunker) -> None:
        pieces = [("abc", 0, 3), ("def", 3, 6), ("g" * 10, 6, 16)]
        merged = chunker._merge_pieces(pieces)
        assert merged == [("abcdef", 0, 6), ("g" * 10, 6, 16)]

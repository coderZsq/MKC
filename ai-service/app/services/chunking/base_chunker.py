from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.chunk import Chunk
from app.services.chunking.config import ChunkingConfig
from app.services.chunking.token_estimator import TokenEstimator


class BaseChunker(ABC):
    """Abstract base class shared by all chunking strategies."""

    def __init__(
        self,
        config: ChunkingConfig,
        estimator: TokenEstimator | None = None,
    ) -> None:
        self.config = config
        self.estimator = estimator or TokenEstimator()

    @abstractmethod
    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]:
        """Split ``text`` into a list of ``Chunk`` objects."""

    def _make_chunk(
        self,
        text: str,
        resource_id: str,
        metadata: dict,
        index: int,
        start_pos: int,
        end_pos: int,
    ) -> Chunk:
        return Chunk(
            id=f"{resource_id}-{index}",
            resource_id=resource_id,
            index=index,
            text=text,
            start_pos=start_pos,
            end_pos=end_pos,
            metadata=dict(metadata) if self.config.preserve_metadata else {},
            token_count=self.estimator.count(text),
        )

    def _size_exceeded(self, text: str) -> bool:
        """Check whether ``text`` exceeds the configured token or character limit."""
        return (
            len(text) > self.config.chunk_size
            or self.estimator.count(text) > self.config.chunk_size
        )

    def _split_chars(self, text: str, start_pos: int) -> list[tuple[str, int, int]]:
        """Split ``text`` into fixed character chunks as a last resort."""
        pieces: list[tuple[str, int, int]] = []
        size = self.config.chunk_size
        pos = 0
        while pos < len(text):
            end = min(pos + size, len(text))
            pieces.append((text[pos:end], start_pos + pos, start_pos + end))
            pos = end
        return pieces

    def _merge_pieces(
        self,
        pieces: list[tuple[str, int, int]],
    ) -> list[tuple[str, int, int]]:
        """Greedily merge adjacent pieces while staying within size limits."""
        if not pieces:
            return []

        merged: list[tuple[str, int, int]] = [pieces[0]]
        for piece in pieces[1:]:
            prev_text, prev_start, _ = merged[-1]
            cur_text, _, cur_end = piece
            combined = prev_text + cur_text
            if (
                len(combined) <= self.config.chunk_size
                and self.estimator.count(combined) <= self.config.chunk_size
            ):
                merged = merged[:-1] + [(combined, prev_start, cur_end)]
            else:
                merged = merged + [piece]
        return merged

    def _split_text(
        self,
        text: str,
        start_pos: int,
        separators: list[str],
        merge_across: bool = True,
    ) -> list[tuple[str, int, int]]:
        """Recursively split ``text`` using ``separators`` from coarse to fine.

        When ``merge_across`` is ``False`` the pieces produced by the first
        separator are kept as separate chunks. This is used by the semantic
        chunker to avoid merging across Markdown heading boundaries.
        """
        if not text:
            return []
        if not self._size_exceeded(text):
            return [(text, start_pos, start_pos + len(text))]
        if not separators:
            return self._split_chars(text, start_pos)

        sep = separators[0]
        if sep == "":
            return self._split_chars(text, start_pos)

        raw_parts = text.split(sep)
        pieces: list[tuple[str, int, int]] = []
        cursor = start_pos
        for i, part in enumerate(raw_parts):
            piece_text = part if i == 0 else sep + part
            if not piece_text:
                cursor += len(piece_text)
                continue
            pieces.append((piece_text, cursor, cursor + len(piece_text)))
            cursor += len(piece_text)

        sub_pieces: list[tuple[str, int, int]] = []
        for piece_text, piece_start, _ in pieces:
            sub = self._split_text(
                piece_text,
                piece_start,
                separators[1:],
                merge_across=True,
            )
            sub_pieces.extend(sub)

        if merge_across:
            return self._merge_pieces(sub_pieces)
        return sub_pieces

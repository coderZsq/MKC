from __future__ import annotations

import re

from app.models.chunk import Chunk
from app.services.chunking.base_chunker import BaseChunker


class ParagraphChunker(BaseChunker):
    """Chunk by blank-line paragraphs, splitting oversized paragraphs only.

    This strategy preserves paragraph boundaries for cleaned transcripts while
    still ensuring that no single chunk exceeds the configured token limit.

    Note:
        Paragraph boundaries are preserved and ``chunk_overlap`` is not applied.
        Use the ``fixed_token`` strategy when sliding-window overlap is required.
    """

    _PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")
    _SENTENCE_SEPARATORS = ["\n", "。", "！", "？", "；", "，", " ", ""]

    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]:
        if not text:
            return []

        raw_pieces: list[tuple[str, int, int]] = []
        cursor = 0
        for match in self._PARAGRAPH_PATTERN.finditer(text):
            segment = text[cursor : match.start()]
            if segment.strip():
                raw_pieces.append((segment, cursor, match.start()))
            cursor = match.end()

        trailing = text[cursor:]
        if trailing.strip():
            raw_pieces.append((trailing, cursor, len(text)))

        chunks: list[Chunk] = []
        index = 0
        for segment, start_pos, _ in raw_pieces:
            if self._size_exceeded(segment):
                pieces = self._split_text(
                    segment,
                    start_pos,
                    self._SENTENCE_SEPARATORS,
                    merge_across=True,
                )
            else:
                pieces = [(segment, start_pos, start_pos + len(segment))]

            for piece_text, piece_start, piece_end in pieces:
                chunks.append(
                    self._make_chunk(
                        piece_text,
                        resource_id,
                        metadata,
                        index,
                        piece_start,
                        piece_end,
                    )
                )
                index += 1

        return chunks

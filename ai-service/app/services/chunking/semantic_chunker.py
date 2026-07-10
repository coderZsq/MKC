from __future__ import annotations

from app.models.chunk import Chunk
from app.services.chunking.base_chunker import BaseChunker
from app.services.chunking.config import DEFAULT_SEPARATORS


class SemanticChunker(BaseChunker):
    """Chunk by semantic boundaries using a configurable separator hierarchy.

    The default separators progress from coarse Markdown headings down to
    individual characters, preserving chapter/heading boundaries where possible.

    Note:
        This strategy preserves natural boundaries and does not apply
        ``chunk_overlap``. Use the ``fixed_token`` strategy when sliding-window
        overlap is required.
    """

    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]:
        if not text:
            return []

        separators = self.config.separators or DEFAULT_SEPARATORS

        pieces = self._split_text(
            text,
            0,
            separators,
            merge_across=False,
        )

        chunks: list[Chunk] = []
        for index, (piece_text, start_pos, end_pos) in enumerate(pieces):
            chunks.append(
                self._make_chunk(
                    piece_text,
                    resource_id,
                    metadata,
                    index,
                    start_pos,
                    end_pos,
                )
            )
        return chunks

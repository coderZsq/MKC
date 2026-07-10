from __future__ import annotations

import logging

from app.models.chunk import Chunk
from app.services.chunking.base_chunker import BaseChunker

logger = logging.getLogger(__name__)


class FixedTokenChunker(BaseChunker):
    """Chunk by a fixed token window with optional overlap.

    Uses tiktoken when available and degrades to a character-count window when
    the tokenizer cannot be loaded. The overlap is measured in the same units
    as the chunk size (tokens or fallback characters).
    """

    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]:
        if not text:
            return []

        chunks: list[Chunk] = []
        start_pos = 0
        index = 0
        length = len(text)
        chunk_size = self.config.chunk_size
        overlap = max(0, min(self.config.chunk_overlap, chunk_size - 1))

        while start_pos < length:
            end_pos = self._find_max_end(text, start_pos, chunk_size)
            chunk_text = text[start_pos:end_pos]
            chunks.append(
                self._make_chunk(
                    chunk_text,
                    resource_id,
                    metadata,
                    index,
                    start_pos,
                    end_pos,
                )
            )

            if end_pos >= length:
                break

            overlap_chars = self._find_overlap_chars(text, start_pos, end_pos, overlap)
            next_pos = end_pos - overlap_chars
            if next_pos <= start_pos:
                next_pos = start_pos + 1
            start_pos = next_pos
            index += 1

        return chunks

    def _find_max_end(self, text: str, start_pos: int, chunk_size: int) -> int:
        """Return the largest end position whose token count is within the limit."""
        lo = start_pos + 1
        hi = len(text) + 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.estimator.count(text[start_pos:mid]) <= chunk_size:
                lo = mid + 1
            else:
                hi = mid
        return lo - 1

    def _find_overlap_chars(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        overlap: int,
    ) -> int:
        """Return the number of characters to overlap while staying within the token limit."""
        if overlap <= 0 or end_pos <= start_pos:
            return 0

        max_overlap = end_pos - start_pos
        lo = 0
        hi = max_overlap + 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.estimator.count(text[end_pos - mid : end_pos]) <= overlap:
                lo = mid + 1
            else:
                hi = mid
        return lo - 1

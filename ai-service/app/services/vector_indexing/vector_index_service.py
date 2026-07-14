from __future__ import annotations

import logging
from typing import Any

from app.models.asr import AsrResult
from app.models.chunk import Chunk
from app.models.embedding import ChunkInput
from app.models.pdf import PdfDocument
from app.models.vector_record import VectorRecord
from app.services.chunking.chunking_service import ChunkingService
from app.services.embedding.service import EmbeddingService
from app.vector_store.vector_store import VectorStore

logger = logging.getLogger(__name__)


class VectorIndexService:
    """Chunks parsed PDF/ASR results, embeds them, and upserts into the vector store.

    The service is idempotent: before upserting new vectors for a resource it
    deletes all existing vectors scoped to ``resource_id`` and ``user_id``.
    """

    SOURCE_PDF = "pdf"
    SOURCE_AUDIO = "audio"

    def __init__(
        self,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        strategy: str | None = None,
    ) -> None:
        self._chunking = chunking_service
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._strategy = strategy

    def index_pdf(self, user_id: str, resource_id: str, document: dict[str, Any]) -> int:
        """Index a parsed PDF document and return the number of vectors upserted."""
        pdf = PdfDocument.model_validate(document)
        all_chunks: list[Chunk] = []
        for page in pdf.pages:
            if not page.text.strip():
                continue
            metadata = {
                "page": page.page_number,
                "total_pages": pdf.total_pages,
                "source_type": self.SOURCE_PDF,
            }
            chunks = self._chunking.chunk(
                page.text,
                resource_id,
                metadata=metadata,
                strategy=self._strategy,
            )
            all_chunks.extend(chunks)
        return self._upsert_chunks(user_id, resource_id, all_chunks)

    def index_asr(self, user_id: str, resource_id: str, result: dict[str, Any]) -> int:
        """Index an ASR result and return the number of vectors upserted."""
        asr = AsrResult.model_validate(result)
        if not asr.segments:
            logger.info("No ASR segments for resource %s, skipping indexing", resource_id)
            return 0

        full_text, segment_ranges = self._build_asr_text_ranges(asr)
        if not full_text.strip():
            return 0

        chunks = self._chunking.chunk(
            full_text,
            resource_id,
            metadata={"source_type": self.SOURCE_AUDIO},
            strategy=self._strategy,
        )
        mapped_chunks = self._apply_time_ranges(chunks, segment_ranges)
        return self._upsert_chunks(user_id, resource_id, mapped_chunks)

    def _build_asr_text_ranges(
        self,
        asr: AsrResult,
    ) -> tuple[str, list[tuple[int, int, float, float]]]:
        """Join segment texts and record each segment's char/time range.

        Segments are joined with a single space so that chunk positions computed
        by the chunker can be mapped back to segment time ranges.
        """
        parts: list[str] = []
        ranges: list[tuple[int, int, float, float]] = []
        cursor = 0
        for segment in asr.segments:
            text = segment.text
            if not text:
                continue
            if parts:
                cursor += 1  # space separator
            start = cursor
            end = cursor + len(text)
            ranges.append((start, end, segment.start, segment.end))
            parts.append(text)
            cursor = end
        return " ".join(parts), ranges

    def _apply_time_ranges(
        self,
        chunks: list[Chunk],
        segment_ranges: list[tuple[int, int, float, float]],
    ) -> list[Chunk]:
        """Add ``start_time``/``end_time`` metadata to chunks based on segment overlap."""
        if not segment_ranges:
            return chunks

        mapped: list[Chunk] = []
        for chunk in chunks:
            start_time: float | None = None
            end_time: float | None = None
            for seg_start, seg_end, seg_time_start, seg_time_end in segment_ranges:
                overlap = min(chunk.end_pos, seg_end) - max(chunk.start_pos, seg_start)
                if overlap <= 0:
                    continue
                if start_time is None or seg_time_start < start_time:
                    start_time = seg_time_start
                if end_time is None or seg_time_end > end_time:
                    end_time = seg_time_end

            metadata = dict(chunk.metadata)
            if start_time is not None:
                metadata["start_time"] = start_time
            if end_time is not None:
                metadata["end_time"] = end_time
            mapped.append(chunk.model_copy(update={"metadata": metadata}))
        return mapped

    def _upsert_chunks(self, user_id: str, resource_id: str, chunks: list[Chunk]) -> int:
        """Embed chunks and upsert them into the vector store."""
        if not chunks:
            return 0

        chunk_inputs = [
            ChunkInput(id=chunk.id, resource_id=chunk.resource_id, text=chunk.text)
            for chunk in chunks
        ]
        embeddings = self._embedding.embed(chunk_inputs)
        records = [
            VectorRecord(
                id=chunk.id,
                resource_id=chunk.resource_id,
                user_id=user_id,
                text=chunk.text,
                vector=embedding.vector,
                metadata={**chunk.metadata, "chunk_index": chunk.index},
            )
            for chunk, embedding in zip(chunks, embeddings, strict=False)
        ]

        self._vector_store.delete_by_resource(resource_id, user_id=user_id)
        return self._vector_store.upsert(records)

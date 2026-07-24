from __future__ import annotations

from app.models.retrieval import RetrievalChunk
from app.services.chunking.token_estimator import TokenEstimator


class LlamaIndexContextCompressor:
    """Select retrieval chunks until the configured context token budget is reached."""

    def __init__(self, token_estimator: TokenEstimator | None = None) -> None:
        self._token_estimator = token_estimator or TokenEstimator()

    def compress(
        self,
        chunks: list[RetrievalChunk],
        max_context_tokens: int,
    ) -> tuple[list[RetrievalChunk], int]:
        """Return relevance-ordered chunks that fit the token budget.

        Like the legacy retrieval service, the first chunk is kept even when it
        exceeds the budget so a strong single hit is not discarded.
        """
        selected: list[RetrievalChunk] = []
        total_tokens = 0
        for chunk in chunks:
            chunk_tokens = self._token_estimator.count(chunk.text)
            if selected and total_tokens + chunk_tokens > max_context_tokens:
                break
            selected.append(chunk)
            total_tokens += chunk_tokens
        return selected, total_tokens

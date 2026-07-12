from __future__ import annotations

from typing import Any

from app.services.chunking.token_estimator import TokenEstimator
from app.services.summary.summary_llm_provider import SummaryLLMProvider


class MapReduceSummarizer:
    def __init__(
        self,
        llm_provider: SummaryLLMProvider,
        config: dict[str, Any] | None = None,
        token_estimator: TokenEstimator | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._config = config or {}
        self._token_estimator = token_estimator or TokenEstimator()

    def summarize(self, text: str) -> tuple[str, int]:
        chunks = self._split_chunks(text)
        if len(chunks) <= 1:
            return self._llm_provider.summarize_full(text)

        total_tokens = 0
        partials: list[str] = []
        for chunk in chunks:
            summary, tokens = self._llm_provider.summarize_chunk(chunk)
            total_tokens += tokens
            partials.append(summary)

        merged_summary, merge_tokens = self._llm_provider.summarize_full("\n\n".join(partials))
        return merged_summary, total_tokens + merge_tokens

    def _split_chunks(self, text: str) -> list[str]:
        map_reduce_cfg = self._config.get("map_reduce", {})
        limit = int(map_reduce_cfg.get("chunk_token_limit", 3000))
        overlap = int(map_reduce_cfg.get("overlap_tokens", 100))
        if limit <= 0:
            return [text]
        tokens = self._token_estimator.encode(text)
        if len(tokens) <= limit:
            return [text]
        step = max(1, limit - max(0, overlap))
        chunks: list[str] = []
        for start in range(0, len(tokens), step):
            chunks.append(self._token_estimator.decode(tokens[start : start + limit]))
            if start + limit >= len(tokens):
                break
        return chunks

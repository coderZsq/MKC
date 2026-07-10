from __future__ import annotations

from app.core.exceptions import InvalidChunkingStrategyError
from app.models.chunk import Chunk
from app.services.chunking.base_chunker import BaseChunker
from app.services.chunking.config import ChunkingConfig
from app.services.chunking.fixed_token_chunker import FixedTokenChunker
from app.services.chunking.paragraph_chunker import ParagraphChunker
from app.services.chunking.semantic_chunker import SemanticChunker
from app.services.chunking.token_estimator import TokenEstimator


class ChunkingService:
    """Unified entry point for text chunking strategies.

    The service registers the supported chunkers and dispatches to the
    configured default strategy or an explicit per-request override.
    """

    STRATEGY_PARAGRAPH = "paragraph"
    STRATEGY_FIXED_TOKEN = "fixed_token"
    STRATEGY_SEMANTIC = "semantic"

    SUPPORTED_STRATEGIES: set[str] = {
        STRATEGY_PARAGRAPH,
        STRATEGY_FIXED_TOKEN,
        STRATEGY_SEMANTIC,
    }

    def __init__(
        self,
        config: ChunkingConfig,
        estimator: TokenEstimator | None = None,
    ) -> None:
        self.config = config
        self._chunkers: dict[str, BaseChunker] = {
            self.STRATEGY_PARAGRAPH: ParagraphChunker(config, estimator),
            self.STRATEGY_FIXED_TOKEN: FixedTokenChunker(config, estimator),
            self.STRATEGY_SEMANTIC: SemanticChunker(config, estimator),
        }

    def chunk(
        self,
        text: str,
        resource_id: str,
        metadata: dict | None = None,
        strategy: str | None = None,
    ) -> list[Chunk]:
        """Chunk ``text`` using the requested or default strategy."""
        selected = (strategy or self.config.default_strategy).strip().lower()
        chunker = self._chunkers.get(selected)
        if chunker is None:
            raise InvalidChunkingStrategyError(selected)
        return chunker.split(text, resource_id, metadata or {})

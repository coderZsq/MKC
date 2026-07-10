from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.exceptions import EmbeddingUnavailableError
from app.services.embedding.config import EmbeddingConfig

if TYPE_CHECKING:
    from numpy import ndarray
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class OpenSourceEmbeddingProvider:
    """Embedding provider backed by a local sentence-transformers model.

    The model is loaded lazily on the first ``embed`` call so that application
    startup stays fast and tests that never embed anything do not pay the load
    cost. ``sentence-transformers`` is imported lazily for the same reason.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model: SentenceTransformer | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a dense vector for each text in ``texts`` preserving order."""
        if self._model is None:
            self._load_model()

        model = self._model
        assert model is not None

        try:
            vectors: ndarray[Any, Any] = model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=False,
                show_progress_bar=False,
            )
        except Exception as exc:
            logger.exception("Open-source embedding model inference failed")
            raise EmbeddingUnavailableError() from exc

        return [vector.tolist() for vector in vectors]

    def _load_model(self) -> None:
        """Lazy-load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            logger.error("sentence-transformers is not installed")
            raise EmbeddingUnavailableError(
                "开源 embedding 依赖 sentence-transformers，请安装该依赖"
            ) from exc

        try:
            self._model = SentenceTransformer(self._config.model)
        except Exception as exc:
            logger.exception("Failed to load open-source embedding model %s", self._config.model)
            raise EmbeddingUnavailableError() from exc

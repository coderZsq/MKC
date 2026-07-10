from __future__ import annotations

import logging

import zhipuai

from app.core.exceptions import EmbeddingAuthenticationError, EmbeddingUnavailableError
from app.services.embedding.config import EmbeddingConfig

logger = logging.getLogger(__name__)


class ZhipuEmbeddingProvider:
    """Embedding provider backed by the ZhipuAI text-embedding-v3 model."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._client = zhipuai.ZhipuAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=0,  # retries are handled by the embedding service
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a vector for each text in ``texts`` preserving order."""
        try:
            response = self._client.embeddings.create(
                model=self._config.model,
                input=texts,
            )
        except zhipuai.APIAuthenticationError as exc:
            logger.warning("ZhipuAI embedding authentication failed")
            raise EmbeddingAuthenticationError() from exc
        except zhipuai.ZhipuAIError as exc:
            logger.warning("ZhipuAI embedding request failed: %s", exc)
            raise EmbeddingUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error calling ZhipuAI embedding API")
            raise EmbeddingUnavailableError() from exc
        return [item.embedding for item in response.data]

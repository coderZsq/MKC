from __future__ import annotations

import logging

from openai import APIError, AuthenticationError, OpenAI

from app.core.exceptions import EmbeddingAuthenticationError, EmbeddingUnavailableError
from app.services.embedding.config import EmbeddingConfig

logger = logging.getLogger(__name__)


class OpenAiEmbeddingProvider:
    """Embedding provider backed by an OpenAI-compatible embedding endpoint."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._client = OpenAI(
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
        except AuthenticationError as exc:
            logger.warning("OpenAI-compatible embedding authentication failed")
            raise EmbeddingAuthenticationError() from exc
        except APIError as exc:
            logger.warning("OpenAI-compatible embedding request failed: %s", exc)
            raise EmbeddingUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error calling OpenAI-compatible embedding API")
            raise EmbeddingUnavailableError() from exc
        return [item.embedding for item in response.data]

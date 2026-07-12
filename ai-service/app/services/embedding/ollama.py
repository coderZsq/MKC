from __future__ import annotations

import logging

import httpx
from openai import APIError, AuthenticationError, OpenAI

from app.core.exceptions import EmbeddingAuthenticationError, EmbeddingUnavailableError
from app.services.embedding.config import EmbeddingConfig

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider:
    """Embedding provider backed by a local Ollama server.

    Ollama exposes an OpenAI-compatible ``/v1/embeddings`` endpoint, so this
    provider reuses the OpenAI SDK. No API key is required -- a placeholder is
    sent because Ollama ignores it. When the server runs on localhost a
    ``trust_env=False`` HTTP client is used so configured HTTP proxies do not
    intercept local requests (mirroring the LLM Ollama provider).
    """

    provider_name = "Ollama"

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._client = OpenAI(
            api_key=config.api_key or "ollama",
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=0,  # retries are handled by the embedding service
            http_client=_build_http_client(config.base_url),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a vector for each text in ``texts`` preserving order."""
        try:
            response = self._client.embeddings.create(
                model=self._config.model,
                input=texts,
            )
        except AuthenticationError as exc:
            logger.warning("Ollama embedding authentication failed")
            raise EmbeddingAuthenticationError() from exc
        except APIError as exc:
            logger.warning("Ollama embedding request failed: %s", exc)
            raise EmbeddingUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error calling Ollama embedding API")
            raise EmbeddingUnavailableError() from exc
        return [item.embedding for item in response.data]


def _build_http_client(base_url: str) -> httpx.Client | None:
    """Return a proxy-free HTTP client for localhost Ollama servers.

    Local Ollama must not be routed through an HTTP/HTTPS proxy, otherwise
    requests fail when ``HTTP_PROXY``/``HTTPS_PROXY`` are set (common in dev).
    """
    if base_url.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]")):
        return httpx.Client(trust_env=False)
    return None

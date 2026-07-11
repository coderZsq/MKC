from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any, cast

from openai import APIError, APITimeoutError, AuthenticationError, OpenAI

from app.core.exceptions import (
    LLMAuthFailedError,
    LLMStreamError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.config import LLMConfig
from app.services.llm.models import LLMRequest, LLMResponse, LLMStreamChunk, Usage

logger = logging.getLogger(__name__)


class KimiProvider(BaseLLMProvider):
    """Provider backed by the Moonshot Kimi models via the OpenAI-compatible SDK."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=0,  # retries are handled by the LLM client
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=[message.model_dump() for message in request.messages],  # type: ignore[misc]
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
            )
        except AuthenticationError as exc:
            logger.warning("Kimi authentication failed")
            raise LLMAuthFailedError() from exc
        except APITimeoutError as exc:
            logger.warning("Kimi request timed out: %s", exc)
            raise LLMTimeoutError() from exc
        except APIError as exc:
            logger.warning("Kimi request failed: %s", exc)
            raise LLMUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error calling Kimi")
            raise LLMUnavailableError() from exc

        return _parse_response(response, self._config.model)

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        try:
            stream = cast(
                Iterator[object],
                await asyncio.to_thread(
                    self._client.chat.completions.create,  # type: ignore[arg-type]
                    model=self._config.model,
                    messages=[message.model_dump() for message in request.messages],
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=True,
                ),
            )
        except AuthenticationError as exc:
            logger.warning("Kimi streaming authentication failed")
            raise LLMAuthFailedError() from exc
        except APITimeoutError as exc:
            logger.warning("Kimi streaming request timed out: %s", exc)
            raise LLMTimeoutError() from exc
        except APIError as exc:
            logger.warning("Kimi streaming request failed: %s", exc)
            raise LLMUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error starting Kimi stream")
            raise LLMUnavailableError() from exc

        stream = iter(stream)

        try:
            while True:
                chunk = await asyncio.to_thread(_next_chunk, stream)
                if chunk is None:
                    break
                yield _parse_stream_chunk(chunk)
        except LLMStreamError:
            raise
        except Exception as exc:
            logger.exception("Kimi stream interrupted")
            raise LLMStreamError() from exc


def _next_chunk(stream: Iterator[object]) -> object | None:
    try:
        return next(stream)
    except StopIteration:
        return None


def _parse_response(response: object, model: str) -> LLMResponse:
    data = _model_dump(response)
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else "stop"
    usage = data.get("usage", {}) or {}
    return LLMResponse(
        content=content or "",
        model=model,
        finish_reason=finish_reason or "stop",
        usage=Usage(
            prompt_tokens=usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0,
            completion_tokens=usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0,
            total_tokens=usage.get("total_tokens", 0) if isinstance(usage, dict) else 0,
        ),
    )


def _parse_stream_chunk(chunk: object) -> LLMStreamChunk:
    data = _model_dump(chunk)
    choices = data.get("choices", [])
    if not choices:
        return LLMStreamChunk(delta="")
    choice = choices[0]
    if not isinstance(choice, dict):
        return LLMStreamChunk(delta="")
    delta = choice.get("delta", {}) or {}
    content = delta.get("content") if isinstance(delta, dict) else delta
    finish_reason = choice.get("finish_reason")
    return LLMStreamChunk(delta=content or "", finish_reason=finish_reason)


def _model_dump(obj: object) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return cast(dict[str, Any], obj.model_dump())
    if hasattr(obj, "to_dict"):
        return cast(dict[str, Any], obj.to_dict())
    raise TypeError(f"unexpected response type: {type(obj)}")

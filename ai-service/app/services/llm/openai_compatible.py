from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any, cast

import httpx
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI
from openai.types.chat import ChatCompletionMessageParam

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


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for OpenAI-compatible chat-completions APIs."""

    provider_name = "OpenAI-compatible"

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._client = OpenAI(
            api_key=config.api_key or "not-needed",
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=0,  # retries are handled by the LLM client
            http_client=_build_http_client(config.base_url),
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=_message_params(request),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
            )
        except AuthenticationError as exc:
            logger.warning("%s authentication failed", self.provider_name)
            raise LLMAuthFailedError() from exc
        except APITimeoutError as exc:
            logger.warning("%s request timed out: %s", self.provider_name, exc)
            raise LLMTimeoutError() from exc
        except APIError as exc:
            logger.warning("%s request failed: %s", self.provider_name, exc)
            raise LLMUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error calling %s", self.provider_name)
            raise LLMUnavailableError() from exc

        return parse_openai_compatible_response(response, self._config.model)

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        try:
            stream = cast(
                Iterator[object],
                await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=self._config.model,
                    messages=_message_params(request),
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=True,
                ),
            )
        except AuthenticationError as exc:
            logger.warning("%s streaming authentication failed", self.provider_name)
            raise LLMAuthFailedError() from exc
        except APITimeoutError as exc:
            logger.warning("%s streaming request timed out: %s", self.provider_name, exc)
            raise LLMTimeoutError() from exc
        except APIError as exc:
            logger.warning("%s streaming request failed: %s", self.provider_name, exc)
            raise LLMUnavailableError() from exc
        except Exception as exc:
            logger.exception("Unexpected error starting %s stream", self.provider_name)
            raise LLMUnavailableError() from exc

        stream = iter(stream)

        try:
            while True:
                chunk = await asyncio.to_thread(_next_chunk, stream)
                if chunk is None:
                    break
                yield parse_openai_compatible_stream_chunk(chunk)
        except LLMStreamError:
            raise
        except Exception as exc:
            logger.exception("%s stream interrupted", self.provider_name)
            raise LLMStreamError() from exc


def parse_openai_compatible_response(response: object, model: str) -> LLMResponse:
    data = _model_dump(response)
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content, reasoning = _message_content(message) if isinstance(message, dict) else ("", None)
    finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else "stop"
    usage = data.get("usage", {}) or {}
    return LLMResponse(
        content=content,
        reasoning=reasoning,
        model=model,
        finish_reason=finish_reason or "stop",
        usage=Usage(
            prompt_tokens=usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0,
            completion_tokens=usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0,
            total_tokens=usage.get("total_tokens", 0) if isinstance(usage, dict) else 0,
        ),
    )


def parse_openai_compatible_stream_chunk(chunk: object) -> LLMStreamChunk:
    data = _model_dump(chunk)
    choices = data.get("choices", [])
    if not choices:
        return LLMStreamChunk(delta="")
    choice = choices[0]
    if not isinstance(choice, dict):
        return LLMStreamChunk(delta="")
    delta = choice.get("delta", {}) or {}
    content, reasoning = (
        _message_content(delta) if isinstance(delta, dict) else (str(delta or ""), None)
    )
    finish_reason = choice.get("finish_reason")
    return LLMStreamChunk(
        delta=content,
        reasoning_delta=reasoning,
        finish_reason=finish_reason,
    )


def _message_content(message: dict[str, Any]) -> tuple[str, str | None]:
    """Return (content, reasoning) from a message or delta dictionary.

    Reasoning is kept separate so callers can stream it independently of the
    answer content.
    """
    content = str(message.get("content") or "")
    reasoning = message.get("reasoning") or message.get("reasoning_content")
    if reasoning:
        return content, str(reasoning)
    return content, None


def _message_params(request: LLMRequest) -> list[ChatCompletionMessageParam]:
    return cast(
        list[ChatCompletionMessageParam],
        [message.model_dump() for message in request.messages],
    )


def _build_http_client(base_url: str) -> httpx.Client | None:
    if base_url.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]")):
        return httpx.Client(trust_env=False)
    return None


def _next_chunk(stream: Iterator[object]) -> object | None:
    try:
        return next(stream)
    except StopIteration:
        return None


def _model_dump(obj: object) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return cast(dict[str, Any], obj.model_dump())
    if hasattr(obj, "to_dict"):
        return cast(dict[str, Any], obj.to_dict())
    raise TypeError(f"unexpected response type: {type(obj)}")

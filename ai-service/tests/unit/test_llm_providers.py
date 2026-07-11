from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
import zhipuai
from openai import APIError, APITimeoutError, AuthenticationError

from app.core.exceptions import LLMAuthFailedError, LLMTimeoutError, LLMUnavailableError
from app.services.llm.config import LLMConfig
from app.services.llm.kimi_provider import KimiProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.models import LLMRequest, Usage
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.zhipu_provider import ZhipuProvider


async def _collect_stream(stream: AsyncIterator) -> list:
    return [chunk async for chunk in stream]


def _make_request(temperature: float = 0.7, max_tokens: int = 2048) -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": "hello"}],
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _make_complete_response(content: str = "answer") -> MagicMock:
    response = MagicMock()
    response.model_dump.return_value = {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
    }
    return response


def _make_reasoning_response(reasoning: str = "thinking") -> MagicMock:
    response = MagicMock()
    response.model_dump.return_value = {
        "choices": [
            {
                "message": {"content": "", "reasoning": reasoning},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
    }
    return response


def _make_stream_chunk(content: str, finish_reason: str | None = None) -> MagicMock:
    chunk = MagicMock()
    chunk.model_dump.return_value = {
        "choices": [
            {
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ]
    }
    return chunk


def _make_reasoning_stream_chunk(
    reasoning: str, finish_reason: str | None = None
) -> MagicMock:
    chunk = MagicMock()
    chunk.model_dump.return_value = {
        "choices": [
            {
                "delta": {"content": "", "reasoning": reasoning},
                "finish_reason": finish_reason,
            }
        ]
    }
    return chunk


class TestZhipuProvider:
    def test_complete_returns_response(self) -> None:
        cfg = LLMConfig(provider="zhipuai", api_key="dummy")
        with patch("app.services.llm.zhipu_provider.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_complete_response(
                "zhipu answer"
            )
            mock_client_cls.return_value = mock_client

            provider = ZhipuProvider(cfg)
            response = provider.complete(_make_request())

        assert response.content == "zhipu answer"
        assert response.model == "glm-4-flash"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 2
        assert response.usage.completion_tokens == 3
        assert response.usage.total_tokens == 5

    def test_complete_includes_temperature_and_max_tokens(self) -> None:
        cfg = LLMConfig(provider="zhipuai", api_key="dummy")
        with patch("app.services.llm.zhipu_provider.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_complete_response()
            mock_client_cls.return_value = mock_client

            provider = ZhipuProvider(cfg)
            provider.complete(_make_request(temperature=0.5, max_tokens=1024))

            call = mock_client.chat.completions.create.call_args
            assert call.kwargs["temperature"] == 0.5
            assert call.kwargs["max_tokens"] == 1024

    def test_stream_complete_yields_chunks(self) -> None:
        cfg = LLMConfig(provider="zhipuai", api_key="dummy")
        with patch("app.services.llm.zhipu_provider.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = [
                _make_stream_chunk("hello"),
                _make_stream_chunk(" world"),
            ]
            mock_client_cls.return_value = mock_client

            provider = ZhipuProvider(cfg)
            chunks = asyncio.run(_collect_stream(provider.stream_complete(_make_request())))

        assert [chunk.delta for chunk in chunks] == ["hello", " world"]

    def test_auth_error_maps_to_llm_auth_failed(self) -> None:
        cfg = LLMConfig(provider="zhipuai", api_key="dummy")
        with patch("app.services.llm.zhipu_provider.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = zhipuai.APIAuthenticationError(
                "auth failed", response=MagicMock()
            )
            mock_client_cls.return_value = mock_client

            provider = ZhipuProvider(cfg)
            with pytest.raises(LLMAuthFailedError) as exc_info:
                provider.complete(_make_request())
            assert exc_info.value.code == "LLM_AUTH_FAILED"

    def test_timeout_error_maps_to_llm_timeout(self) -> None:
        cfg = LLMConfig(provider="zhipuai", api_key="dummy")
        with patch("app.services.llm.zhipu_provider.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = zhipuai.APITimeoutError(
                request=MagicMock()
            )
            mock_client_cls.return_value = mock_client

            provider = ZhipuProvider(cfg)
            with pytest.raises(LLMTimeoutError) as exc_info:
                provider.complete(_make_request())
            assert exc_info.value.code == "LLM_TIMEOUT"

    def test_api_error_maps_to_llm_unavailable(self) -> None:
        cfg = LLMConfig(provider="zhipuai", api_key="dummy")
        with patch("app.services.llm.zhipu_provider.zhipuai.ZhipuAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = zhipuai.APIStatusError(
                "api error", response=MagicMock()
            )
            mock_client_cls.return_value = mock_client

            provider = ZhipuProvider(cfg)
            with pytest.raises(LLMUnavailableError) as exc_info:
                provider.complete(_make_request())
            assert exc_info.value.code == "LLM_UNAVAILABLE"


class TestKimiProvider:
    def test_complete_returns_response(self) -> None:
        cfg = LLMConfig(provider="kimi", api_key="dummy", model="moonshot-v1-8k")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_complete_response(
                "kimi answer"
            )
            mock_client_cls.return_value = mock_client

            provider = KimiProvider(cfg)
            response = provider.complete(_make_request())

        assert response.content == "kimi answer"
        assert response.model == "moonshot-v1-8k"
        assert response.usage.total_tokens == 5

    def test_stream_complete_yields_chunks(self) -> None:
        cfg = LLMConfig(provider="kimi", api_key="dummy", model="moonshot-v1-8k")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = [
                _make_stream_chunk("kimi"),
                _make_stream_chunk("!"),
            ]
            mock_client_cls.return_value = mock_client

            provider = KimiProvider(cfg)
            chunks = asyncio.run(_collect_stream(provider.stream_complete(_make_request())))

        assert [chunk.delta for chunk in chunks] == ["kimi", "!"]

    def test_auth_error_maps_to_llm_auth_failed(self) -> None:
        cfg = LLMConfig(provider="kimi", api_key="dummy", model="moonshot-v1-8k")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = AuthenticationError(
                "auth failed", response=MagicMock(), body=None
            )
            mock_client_cls.return_value = mock_client

            provider = KimiProvider(cfg)
            with pytest.raises(LLMAuthFailedError) as exc_info:
                provider.complete(_make_request())
            assert exc_info.value.code == "LLM_AUTH_FAILED"

    def test_timeout_error_maps_to_llm_timeout(self) -> None:
        cfg = LLMConfig(provider="kimi", api_key="dummy", model="moonshot-v1-8k")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())
            mock_client_cls.return_value = mock_client

            provider = KimiProvider(cfg)
            with pytest.raises(LLMTimeoutError) as exc_info:
                provider.complete(_make_request())
            assert exc_info.value.code == "LLM_TIMEOUT"

    def test_api_error_maps_to_llm_unavailable(self) -> None:
        cfg = LLMConfig(provider="kimi", api_key="dummy", model="moonshot-v1-8k")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = APIError(
                "api error", request=MagicMock(), body=None
            )
            mock_client_cls.return_value = mock_client

            provider = KimiProvider(cfg)
            with pytest.raises(LLMUnavailableError) as exc_info:
                provider.complete(_make_request())
            assert exc_info.value.code == "LLM_UNAVAILABLE"


class TestOllamaProvider:
    def test_complete_returns_response(self) -> None:
        cfg = LLMConfig(provider="ollama")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_complete_response(
                "ollama answer"
            )
            mock_client_cls.return_value = mock_client

            provider = OllamaProvider(cfg)
            response = provider.complete(_make_request())

        assert response.content == "ollama answer"
        assert response.model == "deepseek-r1:8b"
        assert response.usage.total_tokens == 5

    def test_complete_uses_reasoning_when_content_is_empty(self) -> None:
        cfg = LLMConfig(provider="ollama")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_reasoning_response(
                "ollama reasoning"
            )
            mock_client_cls.return_value = mock_client

            provider = OllamaProvider(cfg)
            response = provider.complete(_make_request())

        assert response.content == "ollama reasoning"

    def test_stream_complete_yields_reasoning_chunks(self) -> None:
        cfg = LLMConfig(provider="ollama")
        with patch("app.services.llm.openai_compatible.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = [
                _make_reasoning_stream_chunk("think"),
                _make_stream_chunk(" answer", finish_reason="stop"),
            ]
            mock_client_cls.return_value = mock_client

            provider = OllamaProvider(cfg)
            chunks = asyncio.run(_collect_stream(provider.stream_complete(_make_request())))

        assert [chunk.delta for chunk in chunks] == ["think", " answer"]
        assert chunks[-1].finish_reason == "stop"


class TestMockProvider:
    def test_complete_returns_fixed_text(self) -> None:
        cfg = LLMConfig(provider="mock", mock_response="fixed answer")
        provider = MockProvider(cfg)

        response = provider.complete(_make_request())

        assert response.content == "fixed answer"
        assert response.model == "glm-4-flash"
        assert response.usage == Usage()

    def test_stream_complete_yields_configured_chunks(self) -> None:
        cfg = LLMConfig(provider="mock", mock_stream_chunks=["one", "two", "three"])
        provider = MockProvider(cfg)

        chunks = asyncio.run(_collect_stream(provider.stream_complete(_make_request())))

        deltas = [chunk.delta for chunk in chunks]
        assert deltas == ["one", "two", "three", ""]
        assert chunks[-1].finish_reason == "stop"

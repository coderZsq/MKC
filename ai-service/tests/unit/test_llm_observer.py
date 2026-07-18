from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from tenacity import wait_none

from app.core.exceptions import LLMUnavailableError
from app.observability.llm.langfuse_observer import LangfuseObserver
from app.observability.llm.langsmith_observer import LangSmithObserver
from app.observability.llm.observer import (
    LLMGenerationEvent,
    LLMObserverConfig,
    NoopObserver,
    Redactor,
    build_llm_observer,
    build_llm_observer_config,
)
from app.services.llm.config import LLMConfig
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMRequest, LLMResponse, Message, Usage


def _request() -> LLMRequest:
    return LLMRequest(messages=[Message(role="user", content="api_key=abc hello")])


def _response() -> LLMResponse:
    return LLMResponse(
        content="secret=xyz answer",
        model="glm-4-flash",
        usage=Usage(prompt_tokens=2, completion_tokens=3, total_tokens=5),
    )


def test_redactor_redacts_and_truncates_sensitive_text() -> None:
    redactor = Redactor(max_prompt_chars=28, max_completion_chars=12)

    prompt = redactor.prompt("api_key=super-secret and some very long prompt")
    completion = redactor.completion("token=secret-value trailing")

    assert "[REDACTED]" in prompt
    assert len(prompt) <= 28
    assert completion.startswith("token=[REDAC")
    assert len(completion) <= 12


def test_build_llm_observer_config_resolves_provider() -> None:
    cfg = build_llm_observer_config(
        {
            "provider": "LangFuse",
            "prompt_version": "qa_v3",
            "redact": "false",
            "max_prompt_chars": "12",
            "max_completion_chars": "14",
        }
    )

    assert cfg.provider == "langfuse"
    assert cfg.prompt_version == "qa_v3"
    assert cfg.redact is False
    assert cfg.max_prompt_chars == 12
    assert cfg.max_completion_chars == 14


def test_provider_missing_config_degrades_to_noop(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    with caplog.at_level(logging.WARNING):
        observer = build_llm_observer({"provider": "langfuse"})

    assert isinstance(observer, NoopObserver)
    assert "LLM_OBSERVER_CONFIG_MISSING" in caplog.text


def test_langfuse_observer_records_generation_with_sanitized_event() -> None:
    generation = MagicMock()
    trace = MagicMock()
    trace.generation = generation
    client = MagicMock()
    client.trace.return_value = trace
    observer = LangfuseObserver(
        LLMObserverConfig(provider="langfuse", prompt_version="qa_v3", max_prompt_chars=20),
        client=client,
    )

    observer.record_generation(
        LLMGenerationEvent(
            trace_id="trace-1",
            prompt_version="qa_v3",
            provider="zhipuai",
            model="glm-4",
            prompt="api_key=secret question",
            completion="safe answer",
            latency_ms=10,
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            status="success",
        )
    )

    trace.generation.assert_called_once()
    kwargs = trace.generation.call_args.kwargs
    assert kwargs["model"] == "glm-4"
    assert "[REDACTED]" in kwargs["input"]
    assert kwargs["usage"]["total"] == 3


def test_langsmith_observer_records_generation_with_metadata() -> None:
    client = MagicMock()
    observer = LangSmithObserver(
        LLMObserverConfig(provider="langsmith", prompt_version="qa_v3"),
        client=client,
    )

    observer.record_generation(
        LLMGenerationEvent(
            trace_id="trace-1",
            prompt_version="qa_v3",
            provider="kimi",
            model="moonshot",
            prompt="hello",
            completion="answer",
            latency_ms=10,
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            status="success",
        )
    )

    client.create_run.assert_called_once()
    metadata = client.create_run.call_args.kwargs["extra"]["metadata"]
    assert metadata["prompt_version"] == "qa_v3"
    assert metadata["total_tokens"] == 3


def test_llm_client_records_generation_event(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = MagicMock()
    provider.complete.return_value = _response()
    observer = MagicMock()
    client = LLMClient(
        provider=provider,
        config=LLMConfig(provider="mock", model="glm-4-flash", max_retries=1),
        observer=observer,
        observer_config=LLMObserverConfig(prompt_version="qa_v3"),
    )

    monkeypatch.setattr(
        "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
    )

    response = client.complete(_request())

    assert response.model == "glm-4-flash"
    observer.record_generation.assert_called_once()
    event = observer.record_generation.call_args.args[0]
    assert event.prompt_version == "qa_v3"
    assert event.model == "glm-4-flash"
    assert event.total_tokens == 5
    assert event.status == "success"


def test_observer_failure_does_not_break_llm_flow(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    provider = MagicMock()
    provider.complete.return_value = _response()
    observer = MagicMock()
    observer.record_generation.side_effect = RuntimeError("observer down")
    client = LLMClient(
        provider=provider,
        config=LLMConfig(provider="mock", model="glm-4-flash", max_retries=1),
        observer=observer,
    )

    monkeypatch.setattr(
        "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
    )

    with caplog.at_level(logging.WARNING):
        response = client.complete(_request())

    assert response.content == "secret=xyz answer"
    assert "LLM observer export failed" in caplog.text


def test_llm_client_records_error_event(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = MagicMock()
    provider.complete.side_effect = LLMUnavailableError("down")
    observer = MagicMock()
    client = LLMClient(
        provider=provider,
        config=LLMConfig(provider="mock", model="glm-4-flash", max_retries=1),
        observer=observer,
    )

    monkeypatch.setattr(
        "app.services.llm.llm_client.wait_exponential", lambda *_, **__: wait_none()
    )

    with pytest.raises(LLMUnavailableError):
        client.complete(_request())

    observer.record_error.assert_called_once()
    event = observer.record_error.call_args.args[0]
    assert event.status == "error"
    assert event.error_code == "LLM_UNAVAILABLE"

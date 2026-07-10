from __future__ import annotations

import pytest

from app.services.llm.config import LLMConfig, build_llm_config


class TestLLMConfig:
    def test_default_values(self) -> None:
        cfg = LLMConfig()
        assert cfg.provider == "zhipuai"
        assert cfg.model == "glm-4-flash"
        assert cfg.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048
        assert cfg.timeout == 60
        assert cfg.max_retries == 3

    def test_kimi_defaults(self) -> None:
        cfg = LLMConfig(provider="kimi")
        assert cfg.provider == "kimi"
        assert cfg.model == "moonshot-v1-8k"
        assert cfg.base_url == "https://api.moonshot.cn/v1"

    def test_validation_rejects_invalid_max_tokens(self) -> None:
        with pytest.raises(ValueError, match="max_tokens"):
            LLMConfig(max_tokens=0)

    def test_validation_rejects_invalid_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout"):
            LLMConfig(timeout=0)

    def test_validation_rejects_negative_retries(self) -> None:
        with pytest.raises(ValueError, match="max_retries"):
            LLMConfig(max_retries=-1)

    def test_empty_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="model"):
            LLMConfig(model="")


class TestBuildLLMConfig:
    def test_build_from_config(self) -> None:
        cfg = build_llm_config(
            {
                "provider": "kimi",
                "model": "moonshot-v1-32k",
                "api_key": "${KIMI_API_KEY:-test-key}",
                "temperature": "0.5",
                "max_tokens": "1024",
                "timeout": "30",
                "max_retries": "5",
                "fallback_model": "moonshot-v1-8k",
            }
        )
        assert cfg.provider == "kimi"
        assert cfg.model == "moonshot-v1-32k"
        assert cfg.api_key == "test-key"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 1024
        assert cfg.timeout == 30
        assert cfg.max_retries == 5
        assert cfg.fallback_model == "moonshot-v1-8k"

    def test_zhipu_api_key_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-env-key")
        cfg = build_llm_config({"provider": "zhipuai", "api_key": ""})
        assert cfg.api_key == "zhipu-env-key"

    def test_kimi_api_key_prefers_kimi_env(self, monkeypatch) -> None:
        monkeypatch.setenv("KIMI_API_KEY", "kimi-env-key")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-env-key")
        cfg = build_llm_config({"provider": "kimi", "api_key": ""})
        assert cfg.api_key == "kimi-env-key"

    def test_mock_stream_chunks_parsed_from_string(self) -> None:
        cfg = build_llm_config({"mock_stream_chunks": "a, b, c"})
        assert cfg.mock_stream_chunks == ["a", "b", "c"]

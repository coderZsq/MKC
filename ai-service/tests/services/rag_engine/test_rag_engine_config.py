from __future__ import annotations

from importlib import reload
from unittest.mock import patch

import pytest

from app.core.exceptions import RagEngineConfigError, RagEngineUnavailableError
from app.services.rag_engine.config import (
    RagEngineConfig,
    build_rag_engine_config,
    require_llamaindex,
)


def test_default_rag_engine_is_legacy() -> None:
    config = build_rag_engine_config({})

    assert config.engine == "legacy"
    assert config.llamaindex_enabled is False


def test_rag_engine_env_can_select_llamaindex() -> None:
    config = build_rag_engine_config({"RAG_ENGINE": "llamaindex"})

    assert config.engine == "llamaindex"
    assert config.llamaindex_enabled is True


def test_rag_engine_env_is_normalized() -> None:
    config = build_rag_engine_config({"RAG_ENGINE": " LLaMaInDeX "})

    assert config.engine == "llamaindex"
    assert config.llamaindex_enabled is True


def test_invalid_rag_engine_is_rejected() -> None:
    with pytest.raises(RagEngineConfigError) as exc_info:
        build_rag_engine_config({"RAG_ENGINE": "bad"})

    assert exc_info.value.code == "RAG_ENGINE_INVALID"
    assert "legacy/llamaindex" in exc_info.value.message


def test_legacy_config_does_not_require_llamaindex() -> None:
    with patch("app.services.rag_engine.config.find_spec", side_effect=AssertionError):
        config = RagEngineConfig(engine="legacy")

    assert config.engine == "legacy"
    assert config.llamaindex_enabled is False


def test_require_llamaindex_reports_missing_dependency() -> None:
    with (
        patch("app.services.rag_engine.config.find_spec", return_value=None),
        pytest.raises(RagEngineUnavailableError) as exc_info,
    ):
        require_llamaindex()

    assert exc_info.value.code == "RAG_ENGINE_UNAVAILABLE"


def test_settings_exposes_rag_engine_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.setenv("RAG_ENGINE", "llamaindex")

    import app.core.config as config_module

    reloaded = reload(config_module)

    assert reloaded.settings.rag_engine.engine == "llamaindex"
    assert reloaded.settings.rag_engine_config.llamaindex_enabled is True

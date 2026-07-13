from importlib import reload
from pathlib import Path

import pytest
from pydantic import ValidationError

import app.core.config as config_module


def test_config_requires_internal_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("GATEWAY_INTERNAL_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        reload(config_module)

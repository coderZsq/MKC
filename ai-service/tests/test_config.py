from importlib import reload

import pytest
from pydantic import ValidationError

import app.core.config as config_module


def test_config_requires_internal_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("GATEWAY_INTERNAL_KEY", raising=False)

    with pytest.raises(ValidationError):
        reload(config_module)

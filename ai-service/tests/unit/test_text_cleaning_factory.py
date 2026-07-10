from __future__ import annotations

import builtins
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import TextCleaningError
from app.services.text_cleaning import TextCleaningService
from app.services.text_cleaning.factory import (
    _create_openai_compatible_client,
    build_text_cleaning_service,
)

_original_import = builtins.__import__


def _make_import_stub(**modules: object):
    def _import(name: str, *args, **kwargs):  # noqa: ANN001
        if name in modules:
            module = modules[name]
            if isinstance(module, BaseException):
                raise module
            return module
        return _original_import(name, *args, **kwargs)

    return _import


class TestBuildTextCleaningService:
    def test_rule_mode_does_not_create_llm_cleaner(self) -> None:
        service = build_text_cleaning_service({"mode": "rule", "enabled": True})
        assert isinstance(service, TextCleaningService)
        assert service.llm_cleaner is None

    def test_llm_mode_without_key_returns_service_with_no_llm(self) -> None:
        with patch("app.services.text_cleaning.factory.settings", MagicMock(zhipu_api_key="")):
            service = build_text_cleaning_service({"mode": "llm", "enabled": True})
        assert service.llm_cleaner is None

    def test_llm_mode_with_key_and_openai_package(self) -> None:
        fake_client = MagicMock()
        fake_openai = MagicMock()
        fake_openai.OpenAI.return_value = fake_client

        with (
            patch(
                "app.services.text_cleaning.factory.settings",
                MagicMock(zhipu_api_key="secret"),
            ),
            patch(
                "app.services.text_cleaning.factory._create_openai_compatible_client"
            ) as mock_create,
        ):
            mock_create.return_value = MagicMock()
            service = build_text_cleaning_service({"mode": "llm", "enabled": True})

        assert service.mode == "llm"
        assert service.llm_cleaner is not None

    def test_hybrid_mode_with_key(self) -> None:
        with patch(
            "app.services.text_cleaning.factory._create_openai_compatible_client"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            with patch(
                "app.services.text_cleaning.factory.settings",
                MagicMock(zhipu_api_key="secret"),
            ):
                service = build_text_cleaning_service({"mode": "hybrid", "enabled": True})

        assert service.mode == "hybrid"
        assert service.llm_cleaner is not None

    def test_llm_mode_with_key_uses_installed_openai(self) -> None:
        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_openai.OpenAI.return_value = fake_client

        with (
            patch(
                "app.services.text_cleaning.factory.settings",
                MagicMock(zhipu_api_key="secret"),
            ),
            patch("builtins.__import__", _make_import_stub(openai=fake_openai)),
        ):
            service = build_text_cleaning_service({"mode": "llm", "enabled": True})

        assert service.llm_cleaner is not None
        fake_openai.OpenAI.assert_called_once_with(api_key="secret")

    def test_llm_mode_with_key_uses_zhipuai_when_openai_missing(self) -> None:
        fake_zhipuai = MagicMock()
        fake_client = MagicMock()
        fake_zhipuai.ZhipuAI.return_value = fake_client

        stub = _make_import_stub(
            openai=ImportError("openai not installed"),
            zhipuai=fake_zhipuai,
        )

        with (
            patch(
                "app.services.text_cleaning.factory.settings",
                MagicMock(zhipu_api_key="secret"),
            ),
            patch("builtins.__import__", stub),
        ):
            service = build_text_cleaning_service({"mode": "llm", "enabled": True})

        assert service.llm_cleaner is not None
        fake_zhipuai.ZhipuAI.assert_called_once_with(api_key="secret")

    def test_llm_mode_without_any_client_package_returns_no_llm(self) -> None:
        stub = _make_import_stub(
            openai=ImportError("openai not installed"),
            zhipuai=ImportError("zhipuai not installed"),
        )

        with (
            patch(
                "app.services.text_cleaning.factory.settings",
                MagicMock(zhipu_api_key="secret"),
            ),
            patch("builtins.__import__", stub),
        ):
            service = build_text_cleaning_service({"mode": "llm", "enabled": True})

        assert service.llm_cleaner is None


class TestCreateOpenAiCompatibleClient:
    def test_raises_when_no_package_installed(self) -> None:
        stub = _make_import_stub(
            openai=ImportError("openai not installed"),
            zhipuai=ImportError("zhipuai not installed"),
        )

        with patch("builtins.__import__", stub), pytest.raises(TextCleaningError):
            _create_openai_compatible_client("secret")

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.clients.llm_client import LlmClient, OpenAiCompatibleClient


class MockOpenAiResponse:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def model_dump(self) -> dict[str, object]:
        return self.data


class MockOpenAiResponseToDict:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def to_dict(self) -> dict[str, object]:
        return self.data


class TestOpenAiCompatibleClient:
    def test_returns_dict_response(self) -> None:
        client = MagicMock()
        expected = {"choices": [{"message": {"content": "cleaned"}}]}
        client.chat.completions.create.return_value = expected

        adapter = OpenAiCompatibleClient(client)
        response = adapter.chat_completions_create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": "prompt"}],
            temperature=0.1,
        )

        assert response == expected
        client.chat.completions.create.assert_called_once_with(
            model="glm-4-flash",
            messages=[{"role": "user", "content": "prompt"}],
            temperature=0.1,
            max_tokens=None,
        )

    def test_returns_model_dump(self) -> None:
        client = MagicMock()
        expected = {"choices": [{"message": {"content": "cleaned"}}]}
        client.chat.completions.create.return_value = MockOpenAiResponse(expected)

        adapter = OpenAiCompatibleClient(client)
        response = adapter.chat_completions_create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": "prompt"}],
            temperature=0.1,
            max_tokens=100,
        )

        assert response == expected

    def test_returns_to_dict(self) -> None:
        client = MagicMock()
        expected = {"choices": [{"message": {"content": "cleaned"}}]}
        client.chat.completions.create.return_value = MockOpenAiResponseToDict(expected)

        adapter = OpenAiCompatibleClient(client)
        response = adapter.chat_completions_create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": "prompt"}],
            temperature=0.1,
        )

        assert response == expected

    def test_raises_on_unexpected_response_type(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value = 123

        adapter = OpenAiCompatibleClient(client)
        with pytest.raises(TypeError):
            adapter.chat_completions_create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": "prompt"}],
                temperature=0.1,
            )


def test_llm_client_protocol_is_runtime_checkable() -> None:
    class ValidClient:
        def chat_completions_create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            max_tokens: int | None = None,
        ) -> dict[str, object]:
            return {}

    assert isinstance(ValidClient(), LlmClient)

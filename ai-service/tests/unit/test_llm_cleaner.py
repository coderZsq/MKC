from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.clients.llm_client import LlmClient
from app.models.asr import AsrSegment
from app.services.text_cleaning.llm_cleaner import LlmCleaner


class FakeLlmClient:
    """A fake LLM client that echoes input or returns configurable responses."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.responses = responses

    def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        content = self._build_content(messages)
        return {"choices": [{"message": {"content": content}}]}

    def _build_content(self, messages: list[dict[str, str]]) -> str:
        if self.responses is not None:
            prompt = messages[0]["content"]
            input_lines = [
                line.strip()
                for line in prompt.splitlines()
                if line.strip() and line.strip()[0].isdigit() and "." in line.strip()[:3]
            ]
            count = len(input_lines)
            return "\n".join(
                f"{idx + 1}. {text}" for idx, text in enumerate(self.responses[:count])
            )
        # Extract numbered lines from the prompt and return them unchanged.
        prompt = messages[0]["content"]
        lines = [
            line.strip()
            for line in prompt.splitlines()
            if line.strip().startswith(("1.", "2.", "3."))
        ]
        return "\n".join(lines)


class TestLlmCleaner:
    def test_clean_batch_preserves_timestamps(self) -> None:
        client = FakeLlmClient(responses=["今天天气好", "适合出门"])
        cleaner = LlmCleaner(client, model="glm-4-flash")
        segments = [
            AsrSegment(start=0.0, end=1.0, text="嗯今天天气好啊"),
            AsrSegment(start=1.0, end=2.0, text="哦适合出门"),
        ]

        cleaned = cleaner.clean_segments(segments)

        assert len(cleaned) == 2
        assert cleaned[0].text == "今天天气好"
        assert cleaned[0].start == 0.0
        assert cleaned[0].end == 1.0
        assert cleaned[1].text == "适合出门"
        assert cleaned[1].start == 1.0
        assert cleaned[1].end == 2.0

    def test_empty_segments_returns_empty(self) -> None:
        client = FakeLlmClient()
        cleaner = LlmCleaner(client, model="glm-4-flash")
        assert cleaner.clean_segments([]) == []

    def test_batch_size_splits_requests(self) -> None:
        client = FakeLlmClient(responses=["a", "b", "c", "d"])
        cleaner = LlmCleaner(client, model="glm-4-flash", batch_size=2)
        segments = [
            AsrSegment(start=0.0, end=1.0, text="1"),
            AsrSegment(start=1.0, end=2.0, text="2"),
            AsrSegment(start=2.0, end=3.0, text="3"),
            AsrSegment(start=3.0, end=4.0, text="4"),
        ]

        cleaned = cleaner.clean_segments(segments)

        assert len(cleaned) == 4
        assert len(client.calls) == 2

    def test_parses_json_array_response(self) -> None:
        client = MagicMock(spec=LlmClient)
        client.chat_completions_create.return_value = {
            "choices": [{"message": {"content": '["cleaned one", "cleaned two"]'}}]
        }
        cleaner = LlmCleaner(client, model="glm-4-flash")
        segments = [
            AsrSegment(start=0.0, end=1.0, text="one"),
            AsrSegment(start=1.0, end=2.0, text="two"),
        ]

        cleaned = cleaner.clean_segments(segments)

        assert cleaned[0].text == "cleaned one"
        assert cleaned[1].text == "cleaned two"

    def test_raises_on_mismatched_response_count(self) -> None:
        client = MagicMock(spec=LlmClient)
        client.chat_completions_create.return_value = {
            "choices": [{"message": {"content": "1. only one"}}]
        }
        cleaner = LlmCleaner(client, model="glm-4-flash")
        segments = [
            AsrSegment(start=0.0, end=1.0, text="one"),
            AsrSegment(start=1.0, end=2.0, text="two"),
        ]

        with pytest.raises(ValueError):
            cleaner.clean_segments(segments)

    def test_raises_on_malformed_response(self) -> None:
        client = MagicMock(spec=LlmClient)
        client.chat_completions_create.return_value = {"unexpected": "shape"}
        cleaner = LlmCleaner(client, model="glm-4-flash")
        segments = [AsrSegment(start=0.0, end=1.0, text="one")]

        with pytest.raises(ValueError):
            cleaner.clean_segments(segments)

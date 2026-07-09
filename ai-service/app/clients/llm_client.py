from __future__ import annotations

from typing import Any, Protocol, cast, runtime_checkable


@runtime_checkable
class LlmClient(Protocol):
    """Protocol for a minimal LLM chat client.

    Implementations must return a chat-completions-shaped dictionary. The
    expected shape is::

        {
            "choices": [
                {"message": {"content": "..."}}
            ]
        }
    """

    def chat_completions_create(  # noqa: D102
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, object]: ...


class OpenAiCompatibleClient:
    """Wrap an OpenAI-compatible client (e.g. zhipuai, openai) to satisfy ``LlmClient``.

    The wrapped client must expose ``chat.completions.create`` and return a response
    with ``model_dump`` or ``to_dict`` methods, or a plain dict.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def chat_completions_create(  # noqa: D102
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if isinstance(response, dict):
            return response
        if hasattr(response, "model_dump"):
            return cast(dict[str, object], response.model_dump())
        if hasattr(response, "to_dict"):
            return cast(dict[str, object], response.to_dict())
        raise TypeError(f"unexpected response type from LLM client: {type(response)}")

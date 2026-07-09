from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.clients.llm_client import LlmClient

from app.models.asr import AsrSegment

logger = logging.getLogger(__name__)


class LlmCleaner:
    """LLM-based deep cleaning for ASR segments.

    Requires a client that implements :class:`LlmClient`. The cleaner preserves
    timestamps by returning new ``AsrSegment`` instances with only ``text`` updated.
    """

    def __init__(
        self,
        client: LlmClient,
        model: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        batch_size: int = 10,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.batch_size = max(1, batch_size)

    def clean_segments(self, segments: list[AsrSegment]) -> list[AsrSegment]:
        """Clean all segments in batches, preserving original timestamps."""
        if not segments:
            return []

        cleaned: list[AsrSegment] = []
        for offset in range(0, len(segments), self.batch_size):
            batch = segments[offset : offset + self.batch_size]
            cleaned.extend(self._clean_batch(batch))
        return cleaned

    def _clean_batch(self, segments: list[AsrSegment]) -> list[AsrSegment]:
        if not segments:
            return []

        prompt = self._build_prompt([segment.text for segment in segments])
        response = self.client.chat_completions_create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = self._extract_content(response)
        cleaned_texts = self._parse_response(content, len(segments))
        return [
            segment.model_copy(update={"text": cleaned_text})
            for segment, cleaned_text in zip(segments, cleaned_texts, strict=True)
        ]

    @staticmethod
    def _build_prompt(texts: list[str]) -> str:
        """Build a prompt that asks the model to clean each segment on a new line."""
        lines = "\n".join(f"{idx + 1}. {text}" for idx, text in enumerate(texts))
        return (
            "你是一名语音转录校对专家。请清洗以下转录文本，删除语气词、重复词和口吃，"
            "保持原意与时间戳不变。只输出清洗后的文本，每行一条，编号与输入保持一致。"
            "不要解释，不要添加额外内容。\n\n"
            f"{lines}\n\n"
            "输出："
        )

    @staticmethod
    def _extract_content(response: dict[str, object]) -> str:
        """Extract the assistant message content from a chat completions response."""
        try:
            choices = response["choices"]
            if not isinstance(choices, list):
                raise ValueError("choices is not a list")
            message = choices[0]["message"]
            if not isinstance(message, dict):
                raise ValueError("message is not a dict")
            content = message["content"]
            if not isinstance(content, str):
                raise ValueError("content is not a string")
            return content
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("failed to extract LLM response content: %s", exc)
            raise ValueError(f"unexpected LLM response shape: {exc}") from exc

    @staticmethod
    def _parse_response(content: str, expected_count: int) -> list[str]:
        """Parse a numbered response into the same number of cleaned texts."""
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        # If the model returned a JSON array, prefer it.
        parsed = LlmCleaner._try_parse_json_array(content)
        if parsed is not None and len(parsed) == expected_count:
            return parsed

        # Otherwise, strip leading numbering like "1. " or "1) " from each line.
        cleaned: list[str] = []
        for line in lines:
            stripped = re.sub(r"^\d+[\.\)\s]+", "", line).strip()
            if stripped:
                cleaned.append(stripped)

        if len(cleaned) != expected_count:
            raise ValueError(f"expected {expected_count} cleaned texts, got {len(cleaned)}")
        return cleaned

    @staticmethod
    def _try_parse_json_array(content: str) -> list[str] | None:
        """Attempt to parse the response as a JSON array of strings."""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return parsed
        except json.JSONDecodeError:
            pass
        return None

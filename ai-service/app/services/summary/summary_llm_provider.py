from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import APIException
from app.services.llm import LLMClient
from app.services.llm.models import LLMRequest, Message


class SummaryParseError(APIException):
    def __init__(self, message: str = "摘要结果解析失败") -> None:
        super().__init__("SUMMARY_PARSE_FAILED", message, 422)


class SummaryLLMProvider:
    def __init__(self, llm_client: LLMClient, config: dict[str, Any] | None = None) -> None:
        self._llm_client = llm_client
        self._config = config or {}
        prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
        self._env = Environment(
            loader=FileSystemLoader(str(prompt_dir)),
            autoescape=select_autoescape(default_for_string=False),
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True
    )
    def summarize_full(self, content: str) -> tuple[str, int]:
        prompt = self.render_template(
            "full_summary.j2", content=content, chars=self._chars("full_summary_chars", [200, 300])
        )
        return self._complete_summary(prompt)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True
    )
    def summarize_chunk(self, content: str) -> tuple[str, int]:
        prompt = self.render_template(
            "chunk_summary.j2",
            content=content,
            chars=self._chars("section_summary_chars", [80, 150]),
        )
        return self._complete_summary(prompt)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True
    )
    def summarize_section(self, title: str, content: str) -> tuple[str, int]:
        prompt = self.render_template(
            "section_summary.j2",
            section_title=title,
            content=content,
            chars=self._chars("section_summary_chars", [80, 150]),
        )
        return self._complete_summary(prompt)

    def render_template(self, name: str, **kwargs: Any) -> str:
        template = self._env.get_template(name)
        return str(template.render(**kwargs))

    def _complete_summary(self, prompt: str) -> tuple[str, int]:
        llm_cfg = self._config.get("llm", {})
        response = self._llm_client.complete(
            LLMRequest(
                messages=[Message(role="user", content=prompt)],
                temperature=llm_cfg.get("temperature", 0.3),
                max_tokens=llm_cfg.get("max_tokens", 1024),
            )
        )
        payload = self._parse_json(response.content)
        return str(payload.get("summary", "")).strip(), response.usage.total_tokens

    def _parse_json(self, raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SummaryParseError() from exc
        if not isinstance(payload, dict) or "summary" not in payload:
            raise SummaryParseError("摘要结果缺少 summary 字段")
        return payload

    def _chars(self, key: str, default: list[int]) -> list[int]:
        value = self._config.get(key, default)
        if isinstance(value, list) and len(value) == 2:
            return [int(value[0]), int(value[1])]
        return default

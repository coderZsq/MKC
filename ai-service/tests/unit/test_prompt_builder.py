from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import RetrievalUnavailableError
from app.services.retrieval.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def test_build_renders_chunks_and_question(self) -> None:
        template = "{% for c in chunks %}{{ c.text }}{% endfor %} | {{ question }}"
        builder = PromptBuilder(template_text=template)
        chunks = [type("Chunk", (), {"text": "context", "metadata": {"page": 1}})()]

        prompt = builder.build(chunks, "what is this?")

        assert prompt == "context | what is this?"

    def test_build_handles_empty_chunks(self) -> None:
        builder = PromptBuilder(template_text="{% if not chunks %}无相关知识{% endif %}")

        prompt = builder.build([], "question")

        assert "无相关知识" in prompt

    def test_build_loads_template_from_file(self, tmp_path: Path) -> None:
        template_path = tmp_path / "template.txt"
        template_path.write_text("loaded: {{ question }}", encoding="utf-8")
        builder = PromptBuilder(template_path=str(template_path))

        prompt = builder.build([], "q")

        assert prompt == "loaded: q"

    def test_build_uses_default_template_when_file_missing(self) -> None:
        builder = PromptBuilder(template_path="/nonexistent/path.txt")

        prompt = builder.build([], "question")

        assert "知识库助手" in prompt
        assert "无相关知识" in prompt

    def test_build_raises_on_invalid_template(self) -> None:
        with pytest.raises(RetrievalUnavailableError) as exc_info:
            PromptBuilder(template_text="{% for c in chunks %}")  # unclosed loop

        assert exc_info.value.code == "RETRIEVAL_UNAVAILABLE"

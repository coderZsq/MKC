from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, Template, TemplateError, TemplateSyntaxError

from app.core.exceptions import RetrievalUnavailableError

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATE = """你是知识库助手。请基于以下上下文回答用户问题。
上下文：
{% for chunk in chunks %}
[{{ loop.index }}] {{ chunk.text }} （来源：{{ chunk.metadata }}）
{% endfor %}
{% if not chunks %}
无相关知识。
{% endif %}

用户问题：{{ question }}
请给出简洁、准确的回答。
"""


class PromptBuilder:
    """Renders a RAG prompt from retrieved chunks and a user question."""

    def __init__(
        self,
        template_path: str | None = None,
        template_text: str | None = None,
    ) -> None:
        """Load a Jinja2 template from file, text, or fall back to the default.

        Args:
            template_path: Path to a Jinja2 template file. Ignored if the file
                does not exist and the default template is used instead.
            template_text: Raw Jinja2 template string. Takes precedence over
                ``template_path``.
        """
        if template_text is not None:
            try:
                self._template: Template = Template(template_text)
            except TemplateSyntaxError as exc:
                logger.exception("Invalid prompt template syntax")
                raise RetrievalUnavailableError("Prompt 模板语法错误") from exc
        elif template_path is not None and Path(template_path).exists():
            try:
                self._template = Environment().from_string(
                    Path(template_path).read_text(encoding="utf-8"),
                )
            except TemplateSyntaxError as exc:
                logger.exception("Invalid prompt template syntax in %s", template_path)
                raise RetrievalUnavailableError("Prompt 模板语法错误") from exc
        else:
            if template_path is not None:
                logger.warning("Prompt template not found at %s, using default", template_path)
            self._template = Template(_DEFAULT_TEMPLATE)

    def build(self, chunks: list[Any], question: str) -> str:
        """Render the prompt with the given chunks and question."""
        try:
            return self._template.render(chunks=chunks, question=question)
        except TemplateError as exc:
            logger.exception("Failed to render prompt template")
            raise RetrievalUnavailableError("Prompt 渲染失败") from exc

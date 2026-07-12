from __future__ import annotations

from typing import Any

from app.models.summary import SectionSummary, SummarizeRequest, SummaryResult
from app.services.summary.map_reduce_summarizer import MapReduceSummarizer
from app.services.summary.section_splitter import SectionSplitter
from app.services.summary.summary_llm_provider import SummaryLLMProvider
from app.services.summary.summary_repository import SummaryRepository


class SummaryService:
    def __init__(
        self,
        llm_provider: SummaryLLMProvider,
        summarizer: MapReduceSummarizer,
        splitter: SectionSplitter,
        repository: SummaryRepository,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._summarizer = summarizer
        self._splitter = splitter
        self._repository = repository
        self._config = config or {}

    def generate(self, resource_id: str, request: SummarizeRequest) -> SummaryResult:
        text = self._full_text(request)
        result = SummaryResult(resource_id=resource_id, model=self._model_name())

        if "full" in request.types:
            result.full_summary, tokens, fallback = self._safe_full(text)
            result.tokens += tokens
            result.fallback = result.fallback or fallback

        if "section" in request.types:
            sections = self._split_sections(request)
            result.sections = self._summarize_sections(sections)

        self._repository.save(result)
        return result

    def _safe_full(self, text: str) -> tuple[str, int, bool]:
        summary, tokens = self._summarizer.summarize(text)
        if summary.strip():
            return summary.strip(), tokens, False
        return self._fallback_text(text), tokens, True

    def _summarize_sections(self, sections: list[SectionSummary]) -> list[SectionSummary]:
        summarized: list[SectionSummary] = []
        for section in sections:
            if not section.content.strip():
                continue
            summary, _ = self._llm_provider.summarize_section(section.title, section.content)
            summarized.append(section.model_copy(update={"summary": summary}))
        return summarized

    def _split_sections(self, request: SummarizeRequest) -> list[SectionSummary]:
        if request.source_type == "pdf" and request.parsed:
            return self._splitter.split_pdf(request.parsed)
        if request.srt_segments:
            return self._splitter.split_audio(request.srt_segments)
        return []

    def _full_text(self, request: SummarizeRequest) -> str:
        if request.content:
            return request.content
        if request.parsed:
            return "\n".join(str(page.get("text", "")) for page in request.parsed.get("pages", []))
        if request.srt_segments:
            return "\n".join(str(segment.get("text", "")) for segment in request.srt_segments)
        return ""

    def _fallback_text(self, text: str) -> str:
        fallback_cfg = self._config.get("fallback", {})
        limit = int(fallback_cfg.get("empty_summary_chars", 200))
        return text[:limit]

    def _model_name(self) -> str:
        return str(self._config.get("llm", {}).get("model", "mock"))

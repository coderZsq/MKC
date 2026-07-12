from __future__ import annotations

import pytest

from app.models.summary import SummarizeRequest
from app.services.llm.models import LLMRequest, LLMResponse, Usage
from app.services.summary import MapReduceSummarizer, SectionSplitter, SummaryService
from app.services.summary.summary_llm_provider import SummaryLLMProvider, SummaryParseError


class FakeLLMClient:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or [
            '{"summary":"这是一个满足字数要求的中文摘要，用于覆盖全文摘要生成逻辑。"}'
        ]
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        content = self.responses.pop(0) if self.responses else '{"summary":"默认摘要"}'
        return LLMResponse(content=content, model="mock", usage=Usage(total_tokens=7))


class FakeRepository:
    def __init__(self) -> None:
        self.saved = None

    def save(self, result):
        self.saved = result
        return "minio://results/res/summary.json"


def test_summary_provider_parses_json_and_renders_prompt() -> None:
    provider = SummaryLLMProvider(FakeLLMClient(), {"full_summary_chars": [200, 300]})

    summary, tokens = provider.summarize_full("文档内容")

    assert "中文摘要" in summary
    assert tokens == 7
    prompt = provider.render_template("full_summary.j2", content="正文", chars=[200, 300])
    assert "200-300" in prompt
    assert "正文" in prompt


def test_summary_provider_rejects_non_json() -> None:
    provider = SummaryLLMProvider(FakeLLMClient(["not-json", "not-json", "not-json"]))

    with pytest.raises(SummaryParseError):
        provider.summarize_full("文档内容")


def test_section_splitter_pdf_toc_page_ranges() -> None:
    parsed = {
        "toc": [{"title": "概述", "page": 1}, {"title": "方案", "page": 3}],
        "pages": [{"text": "p1"}, {"text": "p2"}, {"text": "p3"}],
    }

    sections = SectionSplitter().split_pdf(parsed)

    assert [section.title for section in sections] == ["概述", "方案"]
    assert sections[0].page_range == [1, 2]
    assert sections[1].page_range == [3, 3]
    assert "p1" in sections[0].content


def test_section_splitter_audio_ranges() -> None:
    segments = [
        {"start": 0, "end": 120, "text": "开场"},
        {"start": 120, "end": 360, "text": "主题"},
    ]

    sections = SectionSplitter().split_audio(segments, chunk_minutes=5)

    assert sections[0].timestamp_range == [0.0, 360.0]
    assert "开场" in sections[0].content


def test_map_reduce_summarizer_splits_long_text() -> None:
    provider = SummaryLLMProvider(
        FakeLLMClient(
            [
                '{"summary":"分块一"}',
                '{"summary":"分块二"}',
                '{"summary":"最终摘要"}',
            ]
        )
    )
    summarizer = MapReduceSummarizer(
        provider, {"map_reduce": {"chunk_token_limit": 1, "overlap_tokens": 0}}
    )

    summary, tokens = summarizer.summarize("abcdefghij")

    assert summary == "最终摘要"
    assert tokens == 21


def test_summary_service_generates_and_saves_fallback_for_empty_summary() -> None:
    llm_provider = SummaryLLMProvider(FakeLLMClient(['{"summary":""}', '{"summary":"章节摘要"}']))
    repo = FakeRepository()
    service = SummaryService(
        llm_provider=llm_provider,
        summarizer=MapReduceSummarizer(llm_provider, {"map_reduce": {"chunk_token_limit": 100}}),
        splitter=SectionSplitter(),
        repository=repo,
        config={"fallback": {"empty_summary_chars": 4}, "llm": {"model": "mock"}},
    )

    result = service.generate(
        "res-1",
        SummarizeRequest(
            source_type="pdf",
            content="abcdef",
            parsed={"toc": [{"title": "一", "page": 1}], "pages": [{"text": "章节正文"}]},
        ),
    )

    assert result.full_summary == "abcd"
    assert result.fallback is True
    assert result.sections[0].summary == "章节摘要"
    assert repo.saved == result

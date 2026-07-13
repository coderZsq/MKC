from __future__ import annotations

import pytest

from app.models.extraction import Entity, ExtractTagsRequest
from app.services.extraction import (
    EntityResolver,
    ExtractionService,
    RuleExtractionProvider,
    TagNormalizer,
)
from app.services.extraction.llm_extraction_provider import (
    ExtractionParseError,
    LLMExtractionProvider,
)
from app.services.llm.models import LLMRequest, LLMResponse, Usage


class FakeLLMClient:
    def __init__(self, responses: list[str] | None = None, error: Exception | None = None) -> None:
        self.responses = responses or []
        self.error = error
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self.error:
            raise self.error
        content = self.responses.pop(0) if self.responses else '{"tags":[],"entities":[]}'
        return LLMResponse(content=content, model="mock", usage=Usage(total_tokens=3))


class FakeRepository:
    def __init__(self) -> None:
        self.saved = None

    def save(self, result):
        self.saved = result
        return "minio://results/res/tags.json"


def build_service(llm_provider, repo: FakeRepository) -> ExtractionService:
    return ExtractionService(
        llm_provider=llm_provider,
        rule_provider=RuleExtractionProvider(),
        tag_normalizer=TagNormalizer({"max_count": 10, "synonym_merge": True}),
        entity_resolver=EntityResolver(),
        repository=repo,
    )


def test_llm_provider_parses_tags_and_entities() -> None:
    provider = LLMExtractionProvider(
        FakeLLMClient(
            [
                '{"tags":["机器学习","模型训练","数据集","神经网络","GPU"],'
                '"entities":[{"text":"OpenAI","type":"ORG","mention":"OpenAI"},'
                '{"text":"未知","type":"UNKNOWN","mention":"未知"}]}'
            ]
        )
    )

    result = provider.extract("OpenAI 讨论机器学习")

    assert len(result.tags) == 5
    assert result.entities == [Entity(entity="OpenAI", type="ORG", mention="OpenAI", source="llm")]


def test_llm_provider_rejects_invalid_json_after_retries() -> None:
    provider = LLMExtractionProvider(FakeLLMClient(["bad", "bad", "bad"]))

    with pytest.raises(ExtractionParseError):
        provider.extract("正文")


def test_tag_normalizer_dedupes_synonyms_and_truncates() -> None:
    normalizer = TagNormalizer({"max_count": 3, "synonym_merge": True})

    tags = normalizer.normalize(["AI", "人工智能", "ML", "机器学习", "数据集"])

    assert tags == ["人工智能", "机器学习", "数据集"]


def test_entity_resolver_dedupes_and_filters_empty_values() -> None:
    resolver = EntityResolver()

    entities = resolver.resolve(
        [
            Entity(entity=" OpenAI ", type="ORG", mention="OpenAI"),
            Entity(entity="OpenAI", type="ORG", mention="OpenAI"),
            Entity(entity="", type="PERSON", mention=""),
        ]
    )

    assert entities == [Entity(entity="OpenAI", type="ORG", mention="OpenAI", source="llm")]


def test_rule_provider_extracts_keywords_and_entities() -> None:
    result = RuleExtractionProvider().extract(
        "2026年7月 OpenAI 公司在北京讨论机器学习，机器学习模型训练。"
    )

    assert "机器学习" in result.tags
    assert any(entity.type == "DATE" for entity in result.entities)
    assert any(entity.type == "ORG" for entity in result.entities)


def test_service_falls_back_when_llm_fails() -> None:
    repo = FakeRepository()
    service = build_service(LLMExtractionProvider(FakeLLMClient(error=RuntimeError("down"))), repo)

    result = service.extract(
        "res-1",
        ExtractTagsRequest(content="OpenAI 公司在北京讨论机器学习。", source_type="audio"),
    )

    assert result.fallback is True
    assert result.source == "rule"
    assert repo.saved == result


def test_service_empty_content_returns_empty_fallback() -> None:
    repo = FakeRepository()
    service = build_service(LLMExtractionProvider(FakeLLMClient()), repo)

    result = service.extract("res-1", ExtractTagsRequest(content="  "))

    assert result.tags == []
    assert result.entities == []
    assert result.fallback is True
    assert repo.saved == result

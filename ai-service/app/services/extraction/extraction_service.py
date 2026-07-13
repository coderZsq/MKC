from __future__ import annotations

import logging

from app.models.extraction import Entity, ExtractionResponse, ExtractTagsRequest, Tag
from app.services.extraction.entity_resolver import EntityResolver
from app.services.extraction.extraction_repository import ExtractionRepository
from app.services.extraction.llm_extraction_provider import LLMExtractionProvider
from app.services.extraction.rule_extraction_provider import RuleExtractionProvider
from app.services.extraction.tag_normalizer import TagNormalizer

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(
        self,
        llm_provider: LLMExtractionProvider,
        rule_provider: RuleExtractionProvider,
        tag_normalizer: TagNormalizer,
        entity_resolver: EntityResolver,
        repository: ExtractionRepository,
        config: dict | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._rule_provider = rule_provider
        self._tag_normalizer = tag_normalizer
        self._entity_resolver = entity_resolver
        self._repository = repository
        self._config = config or {}

    def extract(self, resource_id: str, request: ExtractTagsRequest) -> ExtractionResponse:
        content = request.content.strip()
        if not content:
            result = ExtractionResponse(
                resource_id=resource_id,
                tags=[],
                entities=[],
                source="rule",
                fallback=True,
            )
            self._repository.save(result)
            return result

        fallback = False
        try:
            extracted = self._llm_provider.extract(content)
        except Exception as exc:
            logger.warning(
                "LLM extraction failed, falling back to rule provider: %s", type(exc).__name__
            )
            extracted = self._rule_provider.extract(content)
            fallback = True

        tags = self._tag_normalizer.normalize(extracted.tags)
        entities = self._entity_resolver.resolve(extracted.entities)
        source = "rule" if fallback else extracted.source
        response = ExtractionResponse(
            resource_id=resource_id,
            tags=[Tag(tag=tag, source=source) for tag in tags],
            entities=[
                Entity(entity=item.entity, type=item.type, mention=item.mention, source=source)
                for item in entities
            ],
            source=source,
            fallback=fallback,
        )
        self._repository.save(response)
        return response

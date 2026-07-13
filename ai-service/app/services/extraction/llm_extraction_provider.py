from __future__ import annotations

import json
from typing import Any, cast

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import APIException
from app.models.extraction import Entity, EntityType, ExtractionResult
from app.services.llm import LLMClient
from app.services.llm.models import LLMRequest, Message

ALLOWED_TYPES = {"PERSON", "ORG", "DATE", "LOC", "GPE", "MISC"}
PROMPT = """你是一名信息抽取专家。请从文本中抽取关键词标签与命名实体。

要求：
- tags: 5-10 个关键词标签，反映核心主题
- entities: 命名实体，类型只允许 PERSON/ORG/DATE/LOC/GPE/MISC
- 每条实体包含 text、type、mention
- 仅输出 JSON，不要 Markdown

JSON 格式：
{{"tags":["..."],"entities":[{{"text":"...","type":"PERSON","mention":"..."}}]}}

文本：
{content}
"""


class ExtractionParseError(APIException):
    def __init__(self, message: str = "标签实体抽取结果解析失败") -> None:
        super().__init__("EXTRACTION_PARSE_FAILED", message, 422)


class LLMExtractionProvider:
    def __init__(self, llm_client: LLMClient, config: dict[str, Any] | None = None) -> None:
        self._llm_client = llm_client
        self._config = config or {}

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True
    )
    def extract(self, content: str) -> ExtractionResult:
        llm_cfg = self._config.get("llm", {})
        batch_cfg = self._config.get("batch", {})
        max_chars = int(batch_cfg.get("max_chars", self._config.get("max_chars", 4000)))
        prompt = PROMPT.format(content=content[:max_chars])
        response = self._llm_client.complete(
            LLMRequest(
                messages=[Message(role="user", content=prompt)],
                temperature=llm_cfg.get("temperature", 0.1),
                max_tokens=llm_cfg.get("max_tokens", 1024),
            )
        )
        return self._parse_json(response.content)

    def _parse_json(self, raw: str) -> ExtractionResult:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExtractionParseError() from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("tags", []), list):
            raise ExtractionParseError("抽取结果缺少 tags 字段")

        tags = [str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()]
        entities: list[Entity] = []
        for raw_entity in payload.get("entities", []):
            if not isinstance(raw_entity, dict):
                continue
            entity_type = str(raw_entity.get("type", "")).upper().strip()
            if entity_type not in ALLOWED_TYPES:
                continue
            entity = str(raw_entity.get("text") or raw_entity.get("entity") or "").strip()
            mention = str(raw_entity.get("mention") or entity).strip()
            if not entity or not mention:
                continue
            entities.append(
                Entity(
                    entity=entity,
                    type=cast(EntityType, entity_type),
                    mention=mention,
                    source="llm",
                )
            )
        return ExtractionResult(tags=tags, entities=entities, source="llm")

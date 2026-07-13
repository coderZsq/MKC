from __future__ import annotations

import re
from collections import Counter
from typing import cast

from app.models.extraction import Entity, EntityType, ExtractionResult

DATE_PATTERN = re.compile(r"\d{4}年\d{1,2}月(?:\d{1,2}日)?|\d{4}-\d{1,2}-\d{1,2}")
ORG_PATTERN = re.compile(
    r"(?:[一-龥A-Za-z0-9]+(?:公司|大学|学院|研究院|集团)|OpenAI|Google|Microsoft)"
)
GPE_PATTERN = re.compile(r"(北京|上海|深圳|广州|杭州|中国|美国|日本|欧洲)")
WORD_PATTERN = re.compile(r"[一-龥]{2,6}|[A-Za-z][A-Za-z0-9_-]{2,}")
KNOWN_KEYWORDS = (
    "人工智能",
    "机器学习",
    "深度学习",
    "神经网络",
    "自然语言处理",
    "模型训练",
    "数据集",
    "参数调优",
    "过拟合",
)

STOPWORDS = {
    "这个",
    "一个",
    "我们",
    "他们",
    "进行",
    "以及",
    "因此",
    "the",
    "and",
    "for",
    "with",
}


class RuleExtractionProvider:
    def extract(self, content: str) -> ExtractionResult:
        entities: list[Entity] = []
        for pattern, entity_type in (
            (DATE_PATTERN, "DATE"),
            (ORG_PATTERN, "ORG"),
            (GPE_PATTERN, "GPE"),
        ):
            for match in pattern.finditer(content):
                mention = match.group().strip()
                if mention:
                    entities.append(
                        Entity(
                            entity=mention,
                            type=cast(EntityType, entity_type),
                            mention=mention,
                            source="rule",
                        )
                    )
        return ExtractionResult(
            tags=self._extract_keywords(content),
            entities=entities,
            source="rule",
        )

    def _extract_keywords(self, content: str) -> list[str]:
        known = [keyword for keyword in KNOWN_KEYWORDS if keyword in content]
        words = [word.strip() for word in WORD_PATTERN.findall(content)]
        filtered = [word for word in words if word.lower() not in STOPWORDS and len(word) >= 2]
        counts = Counter(filtered)
        result = list(dict.fromkeys(known))
        for word, _count in counts.most_common(10):
            if word not in result:
                result.append(word)
            if len(result) >= 10:
                break
        return result

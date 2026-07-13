from __future__ import annotations

from typing import Any

SYNONYM_MAP = {
    "ai": "人工智能",
    "artificial intelligence": "人工智能",
    "ml": "机器学习",
    "machine learning": "机器学习",
    "nlp": "自然语言处理",
}


class TagNormalizer:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._max_count = int(cfg.get("max_count", 10))
        self._lowercase = bool(cfg.get("normalize_lowercase", False))
        self._synonyms = SYNONYM_MAP if bool(cfg.get("synonym_merge", True)) else {}

    def normalize(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in tags:
            tag = str(raw).strip()
            if not tag:
                continue
            key = tag.lower()
            tag = self._synonyms.get(key, tag)
            if self._lowercase:
                tag = tag.lower()
            dedupe_key = tag.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            result.append(tag)
            if len(result) >= self._max_count:
                break
        return result

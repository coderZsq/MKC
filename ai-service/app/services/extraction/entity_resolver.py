from __future__ import annotations

from app.models.extraction import Entity

ALLOWED_TYPES = {"PERSON", "ORG", "DATE", "LOC", "GPE", "MISC"}


class EntityResolver:
    def resolve(self, entities: list[Entity]) -> list[Entity]:
        seen: set[tuple[str, str, str]] = set()
        result: list[Entity] = []
        for item in entities:
            entity = item.entity.strip()
            mention = item.mention.strip()
            entity_type = item.type.upper()
            if not entity or not mention or entity_type not in ALLOWED_TYPES:
                continue
            key = (entity.lower(), entity_type, mention.lower())
            if key in seen:
                continue
            seen.add(key)
            result.append(
                Entity(entity=entity, type=item.type, mention=mention, source=item.source)
            )
        return result

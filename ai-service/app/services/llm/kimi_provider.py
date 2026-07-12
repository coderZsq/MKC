from __future__ import annotations

from app.services.llm.openai_compatible import OpenAICompatibleProvider


class KimiProvider(OpenAICompatibleProvider):
    """Provider backed by the Moonshot Kimi models via the OpenAI-compatible SDK."""

    provider_name = "Kimi"

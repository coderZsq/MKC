from __future__ import annotations

from app.services.llm.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Provider backed by Ollama's OpenAI-compatible chat API."""

    provider_name = "Ollama"

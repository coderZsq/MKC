from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import find_spec

from app.core.exceptions import RagEngineConfigError, RagEngineUnavailableError

_ALLOWED_ENGINES: set[str] = {"legacy", "llamaindex"}


@dataclass(frozen=True)
class RagEngineConfig:
    """Runtime configuration for selecting the AI Service RAG engine."""

    engine: str = "legacy"
    llamaindex_enabled: bool = False

    def __post_init__(self) -> None:
        normalized = str(self.engine).strip().lower()
        if normalized not in _ALLOWED_ENGINES:
            raise RagEngineConfigError()
        object.__setattr__(self, "engine", normalized)
        object.__setattr__(self, "llamaindex_enabled", normalized == "llamaindex")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> RagEngineConfig:
        env = environ if environ is not None else os.environ
        return cls(engine=env.get("RAG_ENGINE", "legacy"))


def build_rag_engine_config(environ: Mapping[str, str] | None = None) -> RagEngineConfig:
    """Build RAG engine config from environment values."""
    return RagEngineConfig.from_env(environ)


def require_llamaindex() -> None:
    """Raise a clear service error when LlamaIndex core is unavailable."""
    try:
        spec = find_spec("llama_index.core")
    except ModuleNotFoundError as exc:
        raise RagEngineUnavailableError() from exc
    if spec is None:
        raise RagEngineUnavailableError()

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from app.core.config import settings

DEFAULT_PROVIDER: str = "milvus"
DEFAULT_COLLECTION_NAME: str = "mkc_vectors"
DEFAULT_URI: str = "./milvus.db"
DEFAULT_DB_NAME: str = "default"
DEFAULT_FALLBACK_PROVIDER: str = "chroma"
DEFAULT_CHROMA_PATH: str = "./chroma"
DEFAULT_DIMENSIONS: int = 2048
DEFAULT_METRIC_TYPE: str = "COSINE"
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_MIN_WAIT: int = 1
DEFAULT_RETRY_MAX_WAIT: int = 10
DEFAULT_CONNECT_TIMEOUT: float = 10.0

_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def _env_values() -> dict[str, str | None]:
    """Return environment variables merged with ``.env`` values."""
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    dotenv = dotenv_values(env_path) if env_path.exists() else {}
    return {**dotenv, **os.environ}


def _resolve_env_value(value: Any) -> Any:
    """Expand ``${VAR}`` / ``${VAR:-default}`` placeholders in string values."""
    if not isinstance(value, str) or "$" not in value:
        return value
    return _ENV_PLACEHOLDER.sub(_replace_placeholder, value)


def _replace_placeholder(match: re.Match[str]) -> str:
    var_name = match.group(1)
    default = match.group(2)
    env_value = _env_values().get(var_name)
    if env_value is None:
        return default if default is not None else ""
    return env_value


def _parse_int(value: Any, default: int) -> int:
    resolved = _resolve_env_value(value)
    if resolved == "" or resolved is None:
        return default
    return int(resolved)


def _parse_float(value: Any, default: float) -> float:
    resolved = _resolve_env_value(value)
    if resolved == "" or resolved is None:
        return default
    return float(resolved)


def _parse_string(value: Any, default: str) -> str:
    resolved = _resolve_env_value(value)
    if resolved == "" or resolved is None:
        return default
    return str(resolved)


@dataclass
class VectorStoreConfig:
    """Runtime configuration for vector storage."""

    provider: str = DEFAULT_PROVIDER
    collection_name: str = DEFAULT_COLLECTION_NAME
    uri: str = DEFAULT_URI
    db_name: str = DEFAULT_DB_NAME
    user: str = ""
    password: str = ""
    token: str = ""
    fallback_provider: str = DEFAULT_FALLBACK_PROVIDER
    chroma_path: str = DEFAULT_CHROMA_PATH
    dimensions: int = DEFAULT_DIMENSIONS
    metric_type: str = DEFAULT_METRIC_TYPE
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_min_wait: int = DEFAULT_RETRY_MIN_WAIT
    retry_max_wait: int = DEFAULT_RETRY_MAX_WAIT
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            raise ValueError("dimensions 必须大于 0")
        if self.max_retries < 0:
            raise ValueError("max_retries 不能为负数")
        if self.top_k_limit <= 0:
            raise ValueError("top_k_limit 必须大于 0")

    @property
    def top_k_limit(self) -> int:
        return 100


def build_vector_store_config(
    config: dict[str, Any] | None = None,
) -> VectorStoreConfig:
    """Build a ``VectorStoreConfig`` from ``config/ai.yaml`` and environment."""
    cfg = config if config is not None else (settings.ai_config or {}).get("vector_store", {})
    return VectorStoreConfig(
        provider=_parse_string(cfg.get("provider"), DEFAULT_PROVIDER),
        collection_name=_parse_string(cfg.get("collection_name"), DEFAULT_COLLECTION_NAME),
        uri=_parse_string(cfg.get("uri"), DEFAULT_URI),
        db_name=_parse_string(cfg.get("db_name"), DEFAULT_DB_NAME),
        user=_parse_string(cfg.get("user"), ""),
        password=_parse_string(cfg.get("password"), ""),
        token=_parse_string(cfg.get("token"), ""),
        fallback_provider=_parse_string(cfg.get("fallback_provider"), DEFAULT_FALLBACK_PROVIDER),
        chroma_path=_parse_string(cfg.get("chroma_path"), DEFAULT_CHROMA_PATH),
        dimensions=_parse_int(cfg.get("dimensions"), DEFAULT_DIMENSIONS),
        metric_type=_parse_string(cfg.get("metric_type"), DEFAULT_METRIC_TYPE),
        max_retries=_parse_int(cfg.get("max_retries"), DEFAULT_MAX_RETRIES),
        retry_min_wait=_parse_int(cfg.get("retry_min_wait"), DEFAULT_RETRY_MIN_WAIT),
        retry_max_wait=_parse_int(cfg.get("retry_max_wait"), DEFAULT_RETRY_MAX_WAIT),
        connect_timeout=_parse_float(cfg.get("connect_timeout"), DEFAULT_CONNECT_TIMEOUT),
    )

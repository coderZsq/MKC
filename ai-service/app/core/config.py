from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from app.services.rag_engine.config import RagEngineConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "mkc-ai-service"
    debug: bool = True
    env: str = "dev"
    port: int = 5000

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/1"

    internal_api_key: str = Field(
        validation_alias=AliasChoices("internal_api_key", "gateway_internal_key")
    )
    log_level: str = "INFO"
    ai_config_path: str = "config/ai.yaml"

    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "mkc-resources"
    minio_endpoint: str = "localhost:9000"
    minio_use_ssl: bool = False
    minio_region: str | None = None

    zhipu_api_key: str = ""
    # ZHIPU_API_KEY can also be set via the environment variable.

    tracing_enabled: bool = True
    tracing_exporter: str = "noop"
    tracing_endpoint: str = ""
    tracing_sample_ratio: float = 0.1
    tracing_service_name: str = "mkc-ai-service"
    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    metrics_namespace: str = "mkc"
    resilience_upload_timeout_seconds: int = 60
    resilience_retrieval_timeout_seconds: int = 20
    resilience_llm_timeout_seconds: int = 60
    resilience_max_retries: int = 2
    resilience_retry_backoff_ms: int = 300

    @property
    def ai_config(self) -> dict[str, Any]:
        return load_yaml_config(self.ai_config_path)

    @property
    def rag_engine_config(self) -> "RagEngineConfig":
        from app.services.rag_engine.config import build_rag_engine_config

        return build_rag_engine_config()

    @property
    def rag_engine(self) -> "RagEngineConfig":
        return self.rag_engine_config

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "dev"


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML configuration file, returning an empty dict on missing file."""
    config_path = Path(path)
    if not config_path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        config_path = project_root / config_path

    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


settings = Settings()  # type: ignore[call-arg]

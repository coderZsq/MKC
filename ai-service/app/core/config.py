from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "dev"


settings = Settings()  # type: ignore[call-arg]

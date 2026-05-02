from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Datathon Predictive Maintenance Platform"
    app_version: str = "0.1.0"
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql://datathon:datathon@localhost:5433/datathon",
        validation_alias="DATABASE_URL",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()

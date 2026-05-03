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
    openai_chat_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias="OPENAI_CHAT_MODEL",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL",
    )
    qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    rag_collection_name: str = Field(default="datathon_docs", validation_alias="RAG_COLLECTION_NAME")
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        validation_alias="MLFLOW_TRACKING_URI",
    )
    drift_report_dir: str = Field(default="reports/drift", validation_alias="DRIFT_REPORT_DIR")


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GROQ_API_KEY: str
    GROQ_AI_MODEL: str
    GROQ_AI_GUARDRAILS_MODEL: str

    WAHA_URL: str = "http://waha:3000"
    WAHA_API_KEY: str
    WAHA_SESSION: str = "default"

    CHROMA_API_KEY: str
    CHROMA_TENANT_ID: str
    CHROMA_DATABASE: str
    CHROMA_COLLECTION_NAME: str = "tcc-grobid-data"

    COHERE_API_KEY: str
    HUGGINGFACE_API_KEY: str | None = None

    ALLOW_ORIGINS: list[str] = Field(default_factory=list)

    HISTORY_MESSAGES_LIMIT: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()

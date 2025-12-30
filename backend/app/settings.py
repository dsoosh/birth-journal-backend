from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"

    database_url: str = Field(validation_alias="DATABASE_URL")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_ttl_seconds: int = Field(default=60 * 60 * 24, validation_alias="JWT_TTL_SECONDS")

    # Firebase Cloud Messaging
    fcm_enabled: bool = Field(default=False, validation_alias="FCM_ENABLED")
    google_application_credentials: str | None = Field(default=None, validation_alias="GOOGLE_APPLICATION_CREDENTIALS")


@lru_cache
def get_settings() -> Settings:
    return Settings()

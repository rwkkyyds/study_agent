"""配置管理。"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-interviewer-system"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    database_url: str = "sqlite:///./interviewer_dev.db"
    jwt_secret_key: str = "local-interviewer-secret-change-before-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    """返回缓存后的配置对象。"""

    return Settings()

"""项目一应用配置。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理环境变量，避免把密钥和环境差异写死在业务代码中。"""

    # 应用基础
    app_name: str = "enterprise-customer-service-rag"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # 数据库：默认 SQLite 本地开发，生产用 PostgreSQL
    database_url: str = "sqlite:///./rag_dev.db"
    db_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求重复读取环境变量。"""

    return Settings()
"""配置管理。"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "local-interviewer-secret-change-before-prod"


class Settings(BaseSettings):
    """应用配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-interviewer-system"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8100",
            "http://127.0.0.1:8100",
        ]
    )
    database_url: str = "sqlite:///./interviewer_dev.db"
    redis_url: str | None = None
    redis_socket_timeout_seconds: float = 2.0
    jwt_secret_key: str = DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 7 * 24 * 60
    stream_token_expire_minutes: int = 5
    login_failure_limit: int = 5
    login_failure_window_seconds: int = 5 * 60
    api_rate_limit_per_minute: int = 30
    api_rate_limit_window_seconds: int = 60
    interview_draft_ttl_seconds: int = 24 * 60 * 60
    interview_task_ttl_seconds: int = 24 * 60 * 60
    interview_task_queue_backend: str = "background"
    interview_task_queue_name: str = "queue:interview_tasks"
    interview_worker_poll_timeout_seconds: int = 5
    max_upload_bytes: int = 5 * 1024 * 1024
    llm_provider: str = "mock"
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    llm_timeout_seconds: float = 15.0
    llm_max_retries: int = 1

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """阻止生产环境继续使用本地开发密钥。"""

        if self.environment.lower() == "production" and self.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
            raise ValueError("生产环境必须通过 JWT_SECRET_KEY 设置非默认密钥")
        return self


@lru_cache
def get_settings() -> Settings:
    """返回缓存后的配置对象。"""

    return Settings()

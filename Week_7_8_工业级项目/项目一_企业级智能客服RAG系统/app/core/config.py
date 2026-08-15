"""项目一应用配置。"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理环境变量，避免把密钥和环境差异写死在业务代码中。"""

    app_name: str = "enterprise-customer-service-rag"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "text"

    database_url: str = "sqlite:///./rag_dev.db"
    db_echo: bool = False

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    dashscope_api_key: str | None = None

    redis_url: str | None = None
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    session_ttl_seconds: int = 3600
    session_max_messages: int = 20

    cors_origins: list[str] = ["*"]

    vector_store_type: str = "memory"
    milvus_uri: str | None = None
    milvus_token: str | None = None
    milvus_collection_name: str = "rag_chunks"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str, info) -> str:
        """生产环境强制要求 JWT 密钥为强随机值（≥32 字节）。"""
        environment = info.data.get("environment", "development")
        if environment == "production":
            if v == "change-me-in-env":
                raise ValueError("生产环境必须设置环境变量 JWT_SECRET_KEY，不能使用默认值")
            if len(v.encode("utf-8")) < 32:
                raise ValueError(f"JWT_SECRET_KEY 长度不足（当前 {len(v)} 字符），建议至少 32 字符")
        return v

    @field_validator("dashscope_api_key")
    @classmethod
    def validate_dashscope_api_key(cls, v: str | None, info) -> str | None:
        """生产环境必须配置 DashScope。"""
        if info.data.get("environment", "development") == "production" and not v:
            raise ValueError("生产环境必须设置 DASHSCOPE_API_KEY")
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str | None, info) -> str | None:
        """生产环境强制要求 Redis 配置。"""
        if info.data.get("environment", "development") == "production" and not v:
            raise ValueError("生产环境必须设置 REDIS_URL")
        return v

    @field_validator("vector_store_type")
    @classmethod
    def validate_vector_store_type(cls, v: str) -> str:
        if v not in {"memory", "milvus"}:
            raise ValueError("VECTOR_STORE_TYPE 必须是 memory 或 milvus")
        return v

    @field_validator("milvus_uri")
    @classmethod
    def validate_milvus_uri(cls, v: str | None, info) -> str | None:
        environment = info.data.get("environment", "development")
        vector_store_type = info.data.get("vector_store_type", "memory")
        if environment == "production" and vector_store_type == "milvus" and not v:
            raise ValueError("生产环境启用 Milvus 时必须设置 MILVUS_URI")
        return v

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

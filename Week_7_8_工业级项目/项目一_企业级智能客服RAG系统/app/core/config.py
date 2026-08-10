"""项目一应用配置。"""

from functools import lru_cache

from pydantic import field_validator
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

    # JWT 认证
    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # 阶段五稳定性：默认使用本地回退，生产环境可通过 Redis URL 启用共享状态
    redis_url: str | None = None
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    session_ttl_seconds: int = 3600
    session_max_messages: int = 20

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str, info) -> str:
        """生产环境强制要求 JWT 密钥为强随机值（≥32 字节）。"""
        environment = info.data.get("environment", "development")
        if environment == "production":
            if v == "change-me-in-env":
                raise ValueError(
                    "生产环境必须设置环境变量 JWT_SECRET_KEY，不能使用默认值"
                )
            if len(v.encode("utf-8")) < 32:
                raise ValueError(
                    f"JWT_SECRET_KEY 长度不足（当前 {len(v)} 字符），建议至少 32 字符"
                )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",   #env_file=".env"：自动加载项目下 .env 文件里的环境变量；
        env_file_encoding="utf-8",
        case_sensitive=False,   # 环境变量名称**不区分大小写**
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求重复读取环境变量。"""

    return Settings()
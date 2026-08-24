"""Redis 客户端封装。"""

from functools import lru_cache
from typing import Any

from app.core.config import Settings, get_settings

try:
    import redis
except ImportError:  # pragma: no cover - 仅用于未安装依赖时的兜底
    redis = None  # type: ignore[assignment]


class RedisUnavailableError(RuntimeError):
    """Redis 配置存在但客户端不可用。"""


def redis_is_configured(settings: Settings | None = None) -> bool:
    """判断当前环境是否启用了 Redis。"""

    resolved_settings = settings or get_settings()
    return bool((resolved_settings.redis_url or "").strip())


def get_redis_client(settings: Settings | None = None) -> Any | None:
    """返回 Redis 客户端；未配置 REDIS_URL 时返回 None。"""

    resolved_settings = settings or get_settings()
    if not redis_is_configured(resolved_settings):
        return None
    return _cached_redis_client(
        resolved_settings.redis_url.strip(),  # type: ignore[union-attr]
        resolved_settings.redis_socket_timeout_seconds,
    )


@lru_cache(maxsize=8)
def _cached_redis_client(redis_url: str, socket_timeout_seconds: float) -> Any:
    if redis is None:
        raise RedisUnavailableError("redis package is not installed")
    return redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=socket_timeout_seconds,
        socket_connect_timeout=socket_timeout_seconds,
    )

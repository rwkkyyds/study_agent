"""阶段五稳定性组件工厂。"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.stability.memory import SessionMemory
from app.stability.rate_limit import AllowAllRateLimiter, SlidingWindowRateLimiter


def build_redis_client(redis_url: str | None) -> Any | None:
    """Redis 可选依赖：未安装、未配置或不可达时返回 None。"""

    if not redis_url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def build_rate_limiter(settings: Settings, redis_client: Any | None = None):
    if settings.rate_limit_requests <= 0:
        return AllowAllRateLimiter()
    return SlidingWindowRateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        redis_client=redis_client,
    )


def build_session_memory(settings: Settings, redis_client: Any | None = None) -> SessionMemory:
    return SessionMemory(
        redis_client=redis_client,
        ttl_seconds=settings.session_ttl_seconds,
        max_messages=settings.session_max_messages,
    )

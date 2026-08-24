"""API 级限流服务。"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.models.user import User
from app.services import redis_client
from app.services.auth import get_current_user

API_RATE_KEY_PREFIX = "rate:"

_api_rate_limits: dict[str, tuple[int, datetime]] = {}


def require_api_rate_limit(route_name: str):
    """FastAPI 依赖工厂：按用户和路由限制高成本接口调用频率。"""

    def limiter(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        check_api_rate_limit(user_id=current_user.id, route_name=route_name or request.url.path)
        return current_user

    return limiter


def check_api_rate_limit(*, user_id: int, route_name: str, limit: int | None = None) -> None:
    """检查并记录一次 API 调用；Redis 启用时使用 Redis，否则使用进程内回退。"""

    settings = get_settings()
    effective_limit = settings.api_rate_limit_per_minute if limit is None else limit
    if effective_limit <= 0:
        return

    normalized_route = _normalize_route_name(route_name)
    if redis_client.redis_is_configured(settings):
        _check_redis_rate_limit(user_id=user_id, route_name=normalized_route, limit=effective_limit)
        return

    _check_local_rate_limit(user_id=user_id, route_name=normalized_route, limit=effective_limit)


def clear_local_api_rate_limits() -> None:
    """清空本地限流状态，供测试隔离使用。"""

    _api_rate_limits.clear()


def _check_redis_rate_limit(*, user_id: int, route_name: str, limit: int) -> None:
    try:
        client = redis_client.get_redis_client()
        if client is None:
            raise redis_client.RedisUnavailableError("redis client is not configured")
        key = _rate_key(user_id=user_id, route_name=route_name)
        attempts = client.incr(key)
        if int(attempts) == 1:
            client.expire(key, get_settings().api_rate_limit_window_seconds + 5)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法执行接口限流") from exc

    if int(attempts) > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="接口调用过于频繁，请稍后再试")


def _check_local_rate_limit(*, user_id: int, route_name: str, limit: int) -> None:
    now = datetime.now(timezone.utc)
    window_seconds = get_settings().api_rate_limit_window_seconds
    key = _rate_key(user_id=user_id, route_name=route_name)
    count, reset_at = _api_rate_limits.get(key, (0, now + timedelta(seconds=window_seconds)))
    if reset_at <= now:
        count = 0
        reset_at = now + timedelta(seconds=window_seconds)

    if count >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="接口调用过于频繁，请稍后再试")

    _api_rate_limits[key] = (count + 1, reset_at)
    _clear_expired_local_rate_limits(now)


def _rate_key(*, user_id: int, route_name: str) -> str:
    minute_bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return f"{API_RATE_KEY_PREFIX}{user_id}:{route_name}:{minute_bucket}"


def _normalize_route_name(route_name: str) -> str:
    return route_name.strip().replace("/", ".").replace(" ", "_").strip(".") or "unknown"


def _clear_expired_local_rate_limits(now: datetime) -> None:
    expired = [key for key, (_count, reset_at) in _api_rate_limits.items() if reset_at <= now]
    for key in expired:
        _api_rate_limits.pop(key, None)

"""客服请求限流：Redis 可用时共享计数，不可用时回退进程内实现。"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Any


class SlidingWindowRateLimiter:
    """按身份执行滑动窗口限流，避免单机开发环境强依赖 Redis。"""

    def __init__(
        self,
        limit: int = 60,
        window_seconds: int = 60,
        redis_client: Any | None = None,
        key_prefix: str = "customer-service:ratelimit",
    ) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit 和 window_seconds 必须大于 0")
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, identity: str) -> bool:
        """记录一次请求；返回是否允许继续处理。"""

        if not identity:
            raise ValueError("identity 不能为空")
        if self.redis is not None:
            return self._allow_redis(identity)
        return self._allow_local(identity)

    def _allow_local(self, identity: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[identity]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True

    def _allow_redis(self, identity: str) -> bool:
        """使用 Redis pipeline；Redis 异常时不阻断客服请求。"""

        try:
            now = time.time()
            key = f"{self.key_prefix}:{identity}"
            member = f"{now}:{uuid.uuid4().hex}"
            pipeline = self.redis.pipeline()
            pipeline.zremrangebyscore(key, 0, now - self.window_seconds)
            pipeline.zadd(key, {member: now})
            pipeline.zcard(key)
            pipeline.expire(key, self.window_seconds)
            count = pipeline.execute()[2]
            if count > self.limit:
                self.redis.zrem(key, member)
                return False
            return True
        except Exception:
            return self._allow_local(identity)


class AllowAllRateLimiter:
    """禁用限流时使用的显式实现，便于测试和本地配置。"""

    def allow(self, identity: str) -> bool:
        return bool(identity)

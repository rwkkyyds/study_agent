"""客服会话记忆：Redis 持久化优先，进程内存储用于本地开发和测试。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class SessionMemory:
    """保存用户最近对话，按 user_id 隔离并限制历史长度。"""

    def __init__(
        self,
        redis_client: Any | None = None,
        ttl_seconds: int = 3600,
        max_messages: int = 20,
        key_prefix: str = "customer-service:session",
    ) -> None:
        if ttl_seconds <= 0 or max_messages <= 0:
            raise ValueError("ttl_seconds 和 max_messages 必须大于 0")
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self.key_prefix = key_prefix
        self._messages: dict[str, list[dict[str, str]]] = {}
        self._lock = Lock()

    def append(self, user_id: int | str, role: str, content: str) -> None:
        if not content.strip():
            raise ValueError("content 不能为空")
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.redis is not None:
            try:
                key = self._key(user_id)
                self.redis.rpush(key, json.dumps(message, ensure_ascii=False))
                self.redis.ltrim(key, -self.max_messages, -1)
                self.redis.expire(key, self.ttl_seconds)
                return
            except Exception:
                pass
        with self._lock:
            messages = self._messages.setdefault(str(user_id), [])
            messages.append(message)
            del messages[:-self.max_messages]

    def recent(self, user_id: int | str, limit: int | None = None) -> list[dict[str, str]]:
        size = min(limit or self.max_messages, self.max_messages)
        if size <= 0:
            return []
        if self.redis is not None:
            try:
                raw = self.redis.lrange(self._key(user_id), -size, -1)
                return [json.loads(item) for item in raw]
            except Exception:
                pass
        with self._lock:
            return list(self._messages.get(str(user_id), [])[-size:])

    def clear(self, user_id: int | str) -> None:
        if self.redis is not None:
            try:
                self.redis.delete(self._key(user_id))
            except Exception:
                pass
        with self._lock:
            self._messages.pop(str(user_id), None)

    def _key(self, user_id: int | str) -> str:
        return f"{self.key_prefix}:{user_id}"

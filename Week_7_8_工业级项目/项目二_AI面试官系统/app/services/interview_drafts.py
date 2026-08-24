"""面试回答草稿服务。"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services import redis_client

DRAFT_KEY_PREFIX = "draft:"

_local_drafts: dict[str, tuple[str, datetime]] = {}


def save_interview_draft(*, session_id: str, question_id: str, answer: str) -> None:
    """保存单题回答草稿；空回答视为清理草稿。"""

    normalized_answer = answer.strip()
    if not normalized_answer:
        delete_interview_draft(session_id=session_id, question_id=question_id)
        return

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            client.setex(
                _draft_key(session_id=session_id, question_id=question_id),
                settings.interview_draft_ttl_seconds,
                json.dumps({"answer": normalized_answer}, ensure_ascii=False),
            )
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法保存面试草稿") from exc

    _clear_expired_local_drafts()
    _local_drafts[_draft_key(session_id=session_id, question_id=question_id)] = (
        normalized_answer,
        _utc_now() + timedelta(seconds=settings.interview_draft_ttl_seconds),
    )


def get_interview_drafts(*, session_id: str) -> dict[str, str]:
    """读取某个面试会话的全部草稿。"""

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            drafts: dict[str, str] = {}
            for key in client.scan_iter(match=f"{DRAFT_KEY_PREFIX}{session_id}:*"):
                question_id = str(key).split(":")[-1]
                answer = _decode_redis_draft(client.get(key))
                if answer:
                    drafts[question_id] = answer
            return drafts
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法读取面试草稿") from exc

    _clear_expired_local_drafts()
    prefix = f"{DRAFT_KEY_PREFIX}{session_id}:"
    return {key.removeprefix(prefix): answer for key, (answer, _expires_at) in _local_drafts.items() if key.startswith(prefix)}


def delete_interview_draft(*, session_id: str, question_id: str) -> None:
    """删除单题草稿。"""

    settings = get_settings()
    key = _draft_key(session_id=session_id, question_id=question_id)
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            client.delete(key)
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法删除面试草稿") from exc

    _local_drafts.pop(key, None)


def clear_interview_drafts(*, session_id: str) -> None:
    """清理某个面试会话的全部草稿。"""

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            keys = list(client.scan_iter(match=f"{DRAFT_KEY_PREFIX}{session_id}:*"))
            if keys:
                client.delete(*keys)
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法清理面试草稿") from exc

    prefix = f"{DRAFT_KEY_PREFIX}{session_id}:"
    for key in [key for key in _local_drafts if key.startswith(prefix)]:
        _local_drafts.pop(key, None)


def clear_local_interview_drafts() -> None:
    """清空本地草稿状态，供测试隔离使用。"""

    _local_drafts.clear()


def _draft_key(*, session_id: str, question_id: str) -> str:
    return f"{DRAFT_KEY_PREFIX}{session_id}:{question_id}"


def _decode_redis_draft(raw: Any) -> str | None:
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    answer = payload.get("answer")
    return answer if isinstance(answer, str) else None


def _clear_expired_local_drafts() -> None:
    now = _utc_now()
    for key in [key for key, (_answer, expires_at) in _local_drafts.items() if expires_at <= now]:
        _local_drafts.pop(key, None)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

"""面试异步任务状态服务。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.interview import InterviewTaskStatusResponse
from app.services import redis_client

TASK_KEY_PREFIX = "task:"

_local_tasks: dict[str, dict[str, Any]] = {}


def create_interview_task(*, task_type: str, session_id: str, user_id: int, message: str) -> InterviewTaskStatusResponse:
    """创建一条面试任务状态记录。"""

    now = _utc_now()
    payload: dict[str, Any] = {
        "task_id": f"task-{uuid4().hex}",
        "task_type": task_type,
        "session_id": session_id,
        "user_id": user_id,
        "status": "queued",
        "progress": 0,
        "message": message,
        "error": None,
        "result": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _save_task(payload)
    return _response(payload)


def mark_interview_task_running(task_id: str, message: str = "任务执行中") -> None:
    """把任务标记为 running。"""

    payload = _require_task(task_id)
    payload.update(
        {
            "status": "running",
            "progress": 20,
            "message": message,
            "error": None,
            "updated_at": _utc_now().isoformat(),
        }
    )
    _save_task(payload)


def mark_interview_task_succeeded(
    task_id: str,
    *,
    result: dict[str, Any] | None = None,
    message: str = "任务已完成",
) -> None:
    """把任务标记为 succeeded，并保存可轮询结果。"""

    payload = _require_task(task_id)
    payload.update(
        {
            "status": "succeeded",
            "progress": 100,
            "message": message,
            "error": None,
            "result": result,
            "updated_at": _utc_now().isoformat(),
        }
    )
    _save_task(payload)


def mark_interview_task_failed(task_id: str, *, error: str, message: str = "任务执行失败") -> None:
    """把任务标记为 failed。"""

    payload = _require_task(task_id)
    payload.update(
        {
            "status": "failed",
            "progress": 100,
            "message": message,
            "error": error,
            "updated_at": _utc_now().isoformat(),
        }
    )
    _save_task(payload)


def get_interview_task(task_id: str) -> dict[str, Any] | None:
    """按任务 ID 获取原始任务状态，包含 user_id 供权限校验。"""

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            raw = client.get(_task_key(task_id))
            return json.loads(raw) if raw else None
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法读取任务状态") from exc

    return _local_tasks.get(task_id)


def task_response(payload: dict[str, Any]) -> InterviewTaskStatusResponse:
    """把原始任务状态转为 API 响应模型。"""

    return _response(payload)


def clear_local_interview_tasks() -> None:
    """清空本地任务状态，供测试隔离使用。"""

    _local_tasks.clear()


def _save_task(payload: dict[str, Any]) -> None:
    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            client.setex(
                _task_key(payload["task_id"]),
                settings.interview_task_ttl_seconds,
                json.dumps(payload, ensure_ascii=False),
            )
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法写入任务状态") from exc

    _local_tasks[payload["task_id"]] = payload


def _require_task(task_id: str) -> dict[str, Any]:
    payload = get_interview_task(task_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return payload


def _response(payload: dict[str, Any]) -> InterviewTaskStatusResponse:
    return InterviewTaskStatusResponse.model_validate(payload)


def _task_key(task_id: str) -> str:
    return f"{TASK_KEY_PREFIX}{task_id}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

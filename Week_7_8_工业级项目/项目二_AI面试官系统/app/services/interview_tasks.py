"""面试异步任务状态服务。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel

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
    session_id: str | None = None,
    message: str = "任务已完成",
) -> None:
    """把任务标记为 succeeded，并保存可轮询结果。"""

    payload = _require_task(task_id)
    updates = {
        "status": "succeeded",
        "progress": 100,
        "message": message,
        "error": None,
        "result": result,
        "updated_at": _utc_now().isoformat(),
    }
    if session_id is not None:
        updates["session_id"] = session_id
    payload.update(updates)
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


def should_use_interview_worker_queue() -> bool:
    """是否应把任务投递到独立 Redis Worker 队列。"""

    settings = get_settings()
    return settings.interview_task_queue_backend == "redis" and redis_client.redis_is_configured(settings)


def enqueue_interview_task_job(
    *,
    task_id: str,
    task_type: str,
    user_id: int,
    request: BaseModel,
) -> bool:
    """把面试任务投递到 Redis 队列；未启用队列时返回 False。"""

    settings = get_settings()
    if not should_use_interview_worker_queue():
        return False

    payload = {
        "task_id": task_id,
        "task_type": task_type,
        "user_id": user_id,
        "request": request.model_dump(mode="json"),
    }
    try:
        client = redis_client.get_redis_client(settings)
        if client is None:
            raise redis_client.RedisUnavailableError("redis client is not configured")
        client.rpush(settings.interview_task_queue_name, json.dumps(payload, ensure_ascii=False))
        return True
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法投递面试任务") from exc


def dequeue_interview_task_job(timeout_seconds: int | None = None) -> dict[str, Any] | None:
    """从 Redis 队列取出一个 Worker 任务。"""

    settings = get_settings()
    try:
        client = redis_client.get_redis_client(settings)
        if client is None:
            raise redis_client.RedisUnavailableError("redis client is not configured")
        timeout = settings.interview_worker_poll_timeout_seconds if timeout_seconds is None else timeout_seconds
        item = client.blpop(settings.interview_task_queue_name, timeout=timeout)
        if item is None:
            return None
        _, raw_payload = item
        return json.loads(raw_payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法消费面试任务") from exc


def interview_worker_queue_status() -> dict[str, Any]:
    """返回异步任务队列配置状态，供 ready 检查展示。"""

    settings = get_settings()
    backend = settings.interview_task_queue_backend
    status_text = "inline_fallback"
    if backend == "redis":
        status_text = "enabled" if redis_client.redis_is_configured(settings) else "misconfigured"
    elif backend != "background":
        status_text = "unsupported_backend"
    return {
        "name": "interview_worker_queue",
        "status": status_text,
        "backend": backend,
        "queue": settings.interview_task_queue_name if backend == "redis" else None,
    }


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

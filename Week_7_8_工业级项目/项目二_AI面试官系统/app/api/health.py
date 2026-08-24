"""健康检查接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.llm_gateway import llm_gateway_status
from app.services.interview_tasks import interview_worker_queue_status
from app.services import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """基础健康检查。"""

    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    """就绪检查。"""

    settings = get_settings()
    dependencies = []

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unready", "dependency": "database"},
        ) from exc

    dependencies.append({"name": "database", "status": "ready"})

    redis_status = "disabled"
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            client.ping()
            redis_status = "ready"
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "unready", "dependency": "redis"},
            ) from exc

    dependencies.append({"name": "redis", "status": redis_status})
    task_queue_status = interview_worker_queue_status()
    dependencies.append(task_queue_status)

    gateway_status = llm_gateway_status(settings)
    dependencies.append(gateway_status)

    qwen_status = "disabled"
    if settings.llm_provider == "qwen":
        qwen_status = "configured" if settings.dashscope_api_key else "missing_api_key"

    dependencies.append(
        {
            "name": "qwen",
            "status": qwen_status,
            "model": settings.qwen_model if qwen_status == "configured" else None,
        }
    )

    return {
        "status": "degraded"
        if gateway_status["status"] in {"missing_api_key", "unsupported_provider"}
        or task_queue_status["status"] in {"misconfigured", "unsupported_backend"}
        else "ready",
        "dependencies": dependencies,
    }

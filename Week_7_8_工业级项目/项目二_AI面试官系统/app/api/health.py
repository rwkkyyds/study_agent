"""健康检查接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

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
        "status": "degraded" if qwen_status == "missing_api_key" else "ready",
        "dependencies": dependencies,
    }

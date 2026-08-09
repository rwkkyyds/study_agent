"""项目一 FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.api.auth import router as auth_router
from app.api.chat import metrics as chat_metrics
from app.api.chat import router as chat_router

from app.core.config import get_settings

from app.db.session import init_db

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库，关闭时清理资源。"""

    logger.info("application_started name=%s version=%s", settings.app_name, settings.app_version)
    init_db()
    yield
    logger.info("application_shutdown name=%s", settings.app_name)


app = FastAPI(
    title="企业级智能客服 RAG 系统",
    version=settings.app_version,
    description="面向企业知识库和客服工单的 RAG 服务。",
    lifespan=lifespan,
)

# 注册路由
app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """提供本地访问入口，并指向 API 文档和健康检查。"""

    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """返回应用存活状态；后续可扩展为依赖服务健康检查。"""

    return {"status": "ok", "environment": settings.environment}


@app.get("/version", tags=["system"])
def version() -> dict[str, str]:
    """返回当前应用版本，便于部署和问题定位。"""

    return {"app": settings.app_name, "version": settings.app_version}


@app.get("/metrics", response_class=PlainTextResponse, tags=["system"])
def metrics() -> str:
    """暴露 Prometheus 文本格式指标。"""

    return chat_metrics.render()





    

"""项目一 FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.chat import metrics as chat_metrics
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.tickets import router as tickets_router

from app.core.config import get_settings
from app.core.logging import configure_logging

from app.db.session import SessionLocal, engine, init_db
from app.models.document import Chunk, Document
from app.rag.retriever import get_shared_retriever
from app.stability.factory import build_redis_client

settings = get_settings()
configure_logging(level=settings.log_level, log_format=settings.log_format)
logger = logging.getLogger(__name__)

# 启动时建立 Redis 客户端（不可达时返回 None，就绪检查会如实报告）
_redis_client = build_redis_client(settings.redis_url)


def _restore_knowledge_index() -> int:
    """从数据库恢复共享检索索引，确保重启后知识库仍可检索。"""

    db = SessionLocal()
    try:
        chunks = (
            db.query(Chunk, Document.title)
            .join(Document, Chunk.document_id == Document.id)
            .order_by(Chunk.document_id, Chunk.chunk_index)
            .all()
        )
        records = [
            (
                f"doc-{chunk.document_id}-chunk-{chunk.chunk_index}",
                chunk.content,
                {"document_id": chunk.document_id, "title": title},
            )
            for chunk, title in chunks
        ]
        restored = get_shared_retriever().index_chunks(records)
        logger.info("knowledge_index_restored chunks=%d", restored)
        return restored
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库并恢复知识库索引。"""

    logger.info("application_started name=%s version=%s", settings.app_name, settings.app_version)
    if settings.environment == "development":
        init_db()
    try:
        _restore_knowledge_index()
    except Exception as exc:
        logger.warning("knowledge_index_restore_failed error=%s", exc)
    yield
    logger.info("application_shutdown name=%s", settings.app_name)


app = FastAPI(
    title="企业级智能客服 RAG 系统",
    version=settings.app_version,
    description="面向企业知识库和客服工单的 RAG 服务。",
    lifespan=lifespan,
)

# ─── CORS 中间件（开发环境允许所有来源，生产环境需收紧） ───────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # 从配置读取
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(tickets_router)

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
def health_check() -> dict:
    """返回应用存活状态与关键依赖（DB/Redis）连通性。"""

    deps = check_dependencies()
    ok = deps["database"] and deps["redis"]
    return {
        "status": "ok" if ok else "degraded",
        "environment": settings.environment,
        "dependencies": deps,
    }


@app.get("/health/live", tags=["system"])
def health_live() -> dict[str, str]:
    """存活探针：进程可响应即返回 200，不检查依赖。"""

    return {"status": "alive"}


@app.get("/health/ready", tags=["system"])
def health_ready() -> dict[str, bool]:
    """就绪探针：校验 DB/Redis 连通性，任一不可用返回 503。

    供容器编排（K8s/Docker Compose healthcheck）使用。
    """

    deps = check_dependencies()
    if not deps["database"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库不可用",
        )
    if not deps["redis"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis 不可用",
        )
    return deps


def check_dependencies() -> dict[str, bool]:
    """探测数据库与 Redis 连通性，返回各依赖的可用状态。"""

    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("healthcheck database unavailable: %s", exc)

    redis_ok = False
    if settings.redis_url:
        if _redis_client is not None:
            try:
                _redis_client.ping()
                redis_ok = True
            except Exception as exc:
                logger.warning("healthcheck redis unavailable: %s", exc)
        else:
            logger.warning("healthcheck redis configured but client is unavailable")
    else:
        # 未配置 Redis（仅限开发环境回退），视为依赖未启用而非故障。
        redis_ok = settings.environment != "production"

    return {"database": db_ok, "redis": redis_ok}


@app.get("/version", tags=["system"])
def version() -> dict[str, str]:
    """返回当前应用版本，便于部署和问题定位。"""

    return {"app": settings.app_name, "version": settings.app_version}


@app.get("/metrics", response_class=PlainTextResponse, tags=["system"])
def metrics() -> str:
    """暴露 Prometheus 文本格式指标。"""

    return chat_metrics.render()





    

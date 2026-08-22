"""应用入口。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.interviews import router as interviews_router
from app.api.question_bank import router as question_bank_router
from app.api.resumes import router as resumes_router
from app.core.config import get_settings

WEB_DIR = Path(__file__).parent / "web"


def create_app() -> FastAPI:
    """创建 FastAPI 应用，方便测试和后续扩展。"""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI 面试官系统：简历理解、题目生成、AI 面试与评分报告。",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(resumes_router)
    app.include_router(question_bank_router)
    app.include_router(interviews_router)
    if WEB_DIR.exists():
        @app.get("/web/console", include_in_schema=False)
        @app.get("/web/console/", include_in_schema=False)
        def serve_console() -> FileResponse:
            """让生产环境也支持面试官控制台的直达入口。"""

            return FileResponse(WEB_DIR / "index.html")

        app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()

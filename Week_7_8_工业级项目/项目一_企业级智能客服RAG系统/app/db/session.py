"""数据库会话管理。

本地开发使用 SQLite（零配置，无需 Docker），
生产环境切换到 PostgreSQL（通过 DATABASE_URL 环境变量）。
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 开发环境用 SQLite，生产环境用 PostgreSQL
# SQLite 连接字符串：sqlite:///./rag_dev.db
# PostgreSQL 连接字符串：postgresql://user:pass@host:5432/dbname
DATABASE_URL = settings.database_url or "sqlite:///./rag_dev.db"

# SQLite 需要 check_same_thread=False（FastAPI 多线程访问）
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=settings.db_echo)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#env_file=".env"：自动加载项目下 .env 文件里的环境变量；
class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类，所有模型继承此基类。"""

    pass


def init_db() -> None:
    """初始化数据库表结构（开发环境自动建表，生产环境用 Alembic 迁移）。"""

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖注入：每个请求获取独立数据库会话，请求结束后自动关闭。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
Demo2: FastAPI + SQLAlchemy 用户系统
功能：用户注册/登录/查询 API，Pydantic ↔ SQLAlchemy 转换
核心：FastAPI 依赖注入 + SQLAlchemy Session 管理
依赖：sqlalchemy, fastapi, uvicorn（已有）
前置：先运行 demo1_sqlalchemy_basics.py 理解 ORM 基础
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import hashlib
from datetime import datetime
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, String, Integer, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from pydantic import BaseModel, EmailStr, Field
from fastapi import FastAPI, Depends, HTTPException


# ========== 1. 数据库配置 ==========
# SQLite（开发用）→ 生产换 PostgreSQL：
# DATABASE_URL = "postgresql+psycopg2://user:pass@localhost:5432/dbname"
DATABASE_URL = "sqlite:///user_system.db"
engine = create_engine(DATABASE_URL, echo=False) # echo=True 输出 SQL 语句，调试用 False 生产环境关闭日志


class Base(DeclarativeBase):
    pass


# ========== 2. SQLAlchemy Model（数据库表） ==========
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self): # 定义对象的字符串表示，方便调试和日志输出
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


# ========== 3. Pydantic Schema（API 请求/响应） ==========
# SQLAlchemy Model = 数据库层（表结构）
# Pydantic Schema = API 层（请求验证 + 响应格式）
# 两者的字段可以不同，需要手动转换

class UserCreate(BaseModel):
    """注册请求"""
    name: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")


class UserLogin(BaseModel):
    """登录请求"""
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户响应（不暴露密码）"""
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime

    class Config: # Pydantic 配置
        from_attributes = True  # 支持从 SQLAlchemy 对象创建 
        # from_attributes=True 允许 Pydantic 从 SQLAlchemy 模型实例中读取属性，自动转换为响应格式

# ========== 4. 数据库会话依赖注入 ==========
# FastAPI 的 Depends 机制：每次请求自动创建 Session，请求结束自动关闭
def get_db():
    """数据库会话依赖注入"""
    db = Session(engine)
    try:
        yield db  # yield 期间请求处理中，finally 保证关闭
    finally:
        db.close()


# ========== 5. 工具函数 ==========
def hash_password(password: str) -> str:
    """密码哈希（生产环境用 bcrypt，这里用 SHA256 简化演示）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return hash_password(password) == password_hash


# ========== 6. FastAPI 应用 ==========
@asynccontextmanager #asynccontextmanager 定义异步上下文管理器，适用于 FastAPI 的 lifespan 生命周期事件
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建表"""
    Base.metadata.create_all(engine)
    print("[OK] 数据库表创建完成")
    yield


app = FastAPI(title="用户系统", lifespan=lifespan)


# ========== 7. API 路由 ==========
@app.post("/register", response_model=UserResponse, summary="用户注册")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册：
    1. 检查邮箱是否已注册
    2. 密码哈希
    3. 创建用户
    """
    # 检查邮箱唯一性
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已注册")

    # 创建用户（密码存哈希）
    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # 刷新获取自增 id

    return user


@app.post("/login", summary="用户登录")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录：
    1. 按 email 查找用户
    2. 验证密码
    """
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="密码错误")

    return {"message": f"登录成功，欢迎 {user.name}！", "user_id": user.id}


@app.get("/users", response_model=list[UserResponse], summary="获取用户列表")
def list_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """分页查询用户列表"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@app.get("/users/{user_id}", response_model=UserResponse, summary="获取单个用户")
def get_user(user_id: int, db: Session = Depends(get_db)):
    """按 ID 查询用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.delete("/users/{user_id}", summary="删除用户")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户（软删除：标记 is_active=False）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = False  # 软删除
    db.commit()
    return {"message": f"用户 {user.name} 已停用"}


# ========== 主函数 ==========
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("FastAPI + SQLAlchemy 用户系统")
    print("=" * 60)
    print("""
    API 文档: http://127.0.0.1:8000/docs

    接口列表:
      POST   /register     用户注册
      POST   /login        用户登录
      GET    /users        用户列表（分页）
      GET    /users/{id}   获取单个用户
      DELETE /users/{id}   删除用户（软删除）

    技术要点:
      1. Pydantic Schema ↔ SQLAlchemy Model 分离
      2. Depends(get_db) 依赖注入数据库会话
      3. 密码哈希存储（不存明文）
      4. 软删除（is_active=False）
    """)

    uvicorn.run(app, host="127.0.0.1", port=8000)

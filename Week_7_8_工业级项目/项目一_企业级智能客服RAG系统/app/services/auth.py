"""认证服务：注册、登录、JWT 令牌管理。

说明：
- 本地开发使用 SQLite，无需外部依赖
- JWT 密钥从环境变量读取，不硬编码
- 密码使用 SHA-256 加盐哈希（生产环境建议换成 bcrypt）
"""

from __future__ import annotations

import datetime
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserCreate

settings = get_settings()
security = HTTPBearer()


def create_user(db: Session, user_data: UserCreate) -> User:
    """创建新用户。如果用户名已存在，抛出 409 冲突。"""

    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    hashed_password, salt = User.hash_password(user_data.password)
    user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        salt=salt,
        role=user_data.role,
        display_name=user_data.display_name,
        email=user_data.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    """验证用户名密码，成功返回 User，失败抛 401。"""

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    return user


def create_access_token(user: User) -> str:
    """生成 JWT access token，过期时间由配置决定。"""

    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT token 解析当前用户，用于保护需要登录的接口。"""

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = int(payload.get("sub", 0))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def require_role(required_role: str):
    """角色权限校验依赖注入：admin/agent/customer。"""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        role_hierarchy = {"admin": 3, "agent": 2, "customer": 1}
        if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user

    return role_checker
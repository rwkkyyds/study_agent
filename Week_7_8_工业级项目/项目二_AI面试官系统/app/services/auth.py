"""认证服务：密码哈希、JWT、当前用户解析和角色校验。"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()
settings = get_settings()
FOLLOW_UP_STREAM_PURPOSE = "interview_follow_up_stream"


def hash_password(password: str) -> str:
    """哈希明文密码。"""

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码。"""

    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_user(db: Session, username: str, password: str, role: str = "candidate") -> User:
    """创建用户，注册入口固定 candidate，管理员入口可指定 role。"""

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    if role not in {"candidate", "admin"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="非法角色")

    user = User(username=username, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """验证用户名密码。"""

    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT。"""

    to_encode = data.copy()
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_follow_up_stream_token(
    *,
    user_id: int,
    session_id: str,
    question_id: str,
    answer: str,
    expires_delta: timedelta | None = None,
) -> str:
    """生成仅用于追问 SSE 连接的短期 Token。"""

    return create_access_token(
        {
            "purpose": FOLLOW_UP_STREAM_PURPOSE,
            "sub": user_id,
            "session_id": session_id,
            "question_id": question_id,
            "answer": answer,
        },
        expires_delta=expires_delta or timedelta(minutes=settings.stream_token_expire_minutes),
    )


def decode_follow_up_stream_token(token: str) -> dict[str, Any]:
    """解析并校验追问 SSE Token。"""

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token") from exc

    required_fields = {"purpose", "sub", "session_id", "question_id", "answer"}
    if payload.get("purpose") != FOLLOW_UP_STREAM_PURPOSE or not required_fields.issubset(payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token")
    try:
        payload["sub"] = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token") from exc
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 Bearer Token 解析当前用户。"""

    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")
        user_id = int(subject)
    except (jwt.PyJWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def require_role(required_role: str):
    """FastAPI 依赖工厂：要求指定角色。"""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"需要 {required_role} 角色")
        return current_user

    return checker

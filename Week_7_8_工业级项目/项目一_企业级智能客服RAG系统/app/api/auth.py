"""认证 API 路由：注册、登录、获取用户信息。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserProfile,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
)

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """注册新用户，默认角色为 customer。"""

    user = create_user(db, payload)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """登录，返回 JWT access token。"""

    user = authenticate_user(db, payload.username, payload.password)
    token = create_access_token(user)
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return TokenResponse(access_token=token, token_type="bearer", expires_at=expire)


@router.get("/me", response_model=UserProfile)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息。"""

    return current_user
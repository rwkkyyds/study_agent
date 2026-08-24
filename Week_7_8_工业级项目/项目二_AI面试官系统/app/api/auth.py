"""认证 API。"""

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AdminCreateUserRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit import record_audit_log
from app.services.auth import (
    authenticate_user,
    blacklist_token_payload,
    clear_login_failures,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_access_token,
    decode_refresh_token,
    get_current_user,
    login_is_rate_limited,
    register_login_failure,
    require_role,
    security,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> User:
    """候选人注册，角色固定为 candidate。"""

    user = create_user(db=db, username=payload.username, password=payload.password, role="candidate")
    record_audit_log(
        db,
        action="auth.register",
        status="success",
        actor_user_id=user.id,
        username=user.username,
        request=request,
    )
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """用户名密码登录。"""

    if login_is_rate_limited(payload.username):
        record_audit_log(
            db,
            action="auth.login",
            status="blocked",
            username=payload.username,
            request=request,
            detail={"reason": "too_many_failed_attempts"},
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="登录失败次数过多，请稍后再试")

    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        register_login_failure(payload.username)
        record_audit_log(
            db,
            action="auth.login",
            status="failed",
            username=payload.username,
            request=request,
            detail={"reason": "bad_credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    clear_login_failures(payload.username)
    record_audit_log(
        db,
        action="auth.login",
        status="success",
        actor_user_id=user.id,
        username=user.username,
        request=request,
    )
    return _token_response_for_user(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """用 refresh token 轮换新的 access token 和 refresh token。"""

    refresh_payload = decode_refresh_token(payload.refresh_token)
    user = db.query(User).filter(User.id == refresh_payload["sub"]).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    blacklist_token_payload(refresh_payload)
    record_audit_log(
        db,
        action="auth.refresh",
        status="success",
        actor_user_id=user.id,
        username=user.username,
        request=request,
    )
    return _token_response_for_user(user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    payload: LogoutRequest | None = Body(default=None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """退出登录：当前 access token 立即失效，可选 refresh token 同步失效。"""

    access_payload = decode_access_token(credentials.credentials)
    blacklist_token_payload(access_payload)

    if payload and payload.refresh_token:
        refresh_payload = decode_refresh_token(payload.refresh_token)
        if refresh_payload["sub"] != current_user.id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新 Token")
        blacklist_token_payload(refresh_payload)

    record_audit_log(
        db,
        action="auth.logout",
        status="success",
        actor_user_id=current_user.id,
        username=current_user.username,
        request=request,
    )
    return MessageResponse(message="已退出登录")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    """当前用户信息。"""

    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUserRequest,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    """管理员创建 candidate/interviewer/hr/admin 用户。"""

    user = create_user(db=db, username=payload.username, password=payload.password, role=payload.role)
    record_audit_log(
        db,
        action="auth.admin_create_user",
        status="success",
        actor_user_id=current_user.id,
        username=current_user.username,
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        detail={"created_username": user.username, "created_role": user.role},
    )
    return user


@router.get("/users", response_model=list[UserResponse])
def admin_list_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    """管理员查看全部用户。"""

    return db.query(User).order_by(User.id.asc()).all()


def _token_response_for_user(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token({"sub": user.id, "role": user.role}),
        refresh_token=create_refresh_token(user_id=user.id, role=user.role),
    )

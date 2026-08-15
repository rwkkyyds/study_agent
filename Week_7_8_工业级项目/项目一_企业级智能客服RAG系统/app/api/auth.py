"""认证 API 路由：注册、登录、获取当前用户。"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import CreateUserRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import authenticate_user, create_access_token, create_user, get_current_user, require_role
from app.models.user import User
from app.stability.factory import build_redis_client
from app.stability.rate_limit import SlidingWindowRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
_login_rate_limiter = SlidingWindowRateLimiter(
    limit=10,
    window_seconds=60,
    redis_client=build_redis_client(settings.redis_url),
    key_prefix="auth:login:ratelimit",
)


def get_login_rate_limiter() -> SlidingWindowRateLimiter:
    """登录接口限流器：每 IP 每分钟最多 10 次尝试。"""
    return _login_rate_limiter


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """注册新用户（固定 customer 角色，不接受客户端指定）。"""

    return create_user(db=db, username=request.username, password=request.password, role="customer")


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    limiter: SlidingWindowRateLimiter = Depends(get_login_rate_limiter),
    raw_request: Request = None,
) -> dict:
    """登录并返回 JWT Token（每 IP 每分钟最多 10 次尝试）。"""

    # 按客户端 IP 限流
    client_ip = raw_request.client.host if raw_request and raw_request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过于频繁，请稍后再试",
        )

    user = authenticate_user(db=db, username=request.username, password=request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token(data={"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """获取当前登录用户的信息。"""

    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    """管理员创建用户，可指定 admin/agent/customer 角色（解决 agent/admin 账号无法创建的问题）。"""

    return create_user(db=db, username=request.username, password=request.password, role=request.role)


@router.get("/users", response_model=list[UserResponse])
def admin_list_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    """管理员查看全部用户列表。"""

    return db.query(User).order_by(User.id).all()

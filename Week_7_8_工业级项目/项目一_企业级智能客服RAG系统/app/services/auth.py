"""认证服务：注册、登录、JWT 生成、身份校验、角色权限。"""

from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()
settings = get_settings()


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（抗 GPU 暴力破解）。"""

    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配。"""

    return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_user(db: Session, username: str, password: str, role: str = "customer") -> User:
    """创建新用户，自动哈希密码。"""

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """验证用户名和密码，返回用户对象或 None。"""

    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT access token。"""

    to_encode = data.copy()
    # PyJWT 要求 sub 为字符串
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖注入：从 JWT 解析当前用户。"""

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")
        user_id = int(subject)  # sub 在签发时转换为字符串，校验时转回 int
    except (jwt.PyJWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def require_role(required_role: str):
    """FastAPI 依赖注入工厂：校验当前用户角色。

    用法：
        @router.get("/admin")
        def admin_only(current_user: User = Depends(require_role("admin"))):
            ...
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 角色",
            )
        return current_user

    return role_checker


def require_any_role(*allowed_roles: str):
    """FastAPI dependency factory: require any one of the allowed roles."""

    allowed = set(allowed_roles)

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下任一角色: {', '.join(sorted(allowed))}",
            )
        return current_user

    return role_checker

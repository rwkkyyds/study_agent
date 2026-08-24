"""认证服务：密码哈希、JWT、当前用户解析和角色校验。"""

import json
import secrets
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
from app.services import redis_client

security = HTTPBearer()

ACCESS_TOKEN_PURPOSE = "access"
REFRESH_TOKEN_PURPOSE = "refresh"
FOLLOW_UP_STREAM_PURPOSE = "interview_follow_up_stream"

STREAM_TOKEN_KEY_PREFIX = "stream_token:"
JWT_BLACKLIST_KEY_PREFIX = "jwt:blacklist:"
LOGIN_FAILURE_KEY_PREFIX = "login_fail:"

VALID_ROLES = {"candidate", "interviewer", "hr", "admin"}

_blacklisted_tokens: dict[str, datetime] = {}
_login_failures: dict[str, tuple[int, datetime]] = {}


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
    if role not in VALID_ROLES:
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
    """生成 JWT access token；显式传入 purpose 时保留调用方用途。"""

    settings = get_settings()
    return _create_jwt_token(
        data={**data, "purpose": data.get("purpose", ACCESS_TOKEN_PURPOSE)},
        expires_delta=expires_delta or timedelta(minutes=settings.jwt_expire_minutes),
    )


def create_refresh_token(*, user_id: int, role: str, expires_delta: timedelta | None = None) -> str:
    """生成 refresh token，用于换取新的 access token。"""

    settings = get_settings()
    return _create_jwt_token(
        data={"purpose": REFRESH_TOKEN_PURPOSE, "sub": user_id, "role": role},
        expires_delta=expires_delta or timedelta(minutes=settings.refresh_token_expire_minutes),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """解析并校验 access token。"""

    payload = _decode_jwt_token(token, invalid_detail="无效的 Token")
    purpose = payload.get("purpose", ACCESS_TOKEN_PURPOSE)
    if purpose != ACCESS_TOKEN_PURPOSE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")
    if is_token_blacklisted(payload.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已失效")
    _normalize_subject(payload, invalid_detail="无效的 Token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """解析并校验 refresh token。"""

    payload = _decode_jwt_token(token, invalid_detail="无效的刷新 Token")
    if payload.get("purpose") != REFRESH_TOKEN_PURPOSE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新 Token")
    if is_token_blacklisted(payload.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新 Token 已失效")
    _normalize_subject(payload, invalid_detail="无效的刷新 Token")
    return payload


def blacklist_token_payload(payload: dict[str, Any]) -> None:
    """把 JWT jti 加入黑名单，TTL 与 token 剩余有效期一致。"""

    jti = payload.get("jti")
    ttl_seconds = _token_ttl_seconds(payload)
    if not jti or ttl_seconds <= 0:
        return

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            client.setex(_blacklist_key(jti), ttl_seconds, "1")
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法失效 Token") from exc

    _clear_expired_blacklisted_tokens()
    _blacklisted_tokens[jti] = _utc_now() + timedelta(seconds=ttl_seconds)


def is_token_blacklisted(jti: Any) -> bool:
    """检查 JWT jti 是否已被加入黑名单。"""

    if not jti:
        return False

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            return bool(client.exists(_blacklist_key(str(jti))))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法校验 Token 状态") from exc

    _clear_expired_blacklisted_tokens()
    return str(jti) in _blacklisted_tokens


def login_is_rate_limited(username: str) -> bool:
    """判断用户名当前是否触发登录失败限流。"""

    settings = get_settings()
    normalized_username = username.strip().lower()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            value = client.get(_login_failure_key(normalized_username))
            return bool(value and int(value) >= settings.login_failure_limit)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法校验登录限流") from exc

    _clear_expired_login_failures()
    count, _reset_at = _login_failures.get(normalized_username, (0, _utc_now()))
    return count >= settings.login_failure_limit


def register_login_failure(username: str) -> None:
    """记录一次登录失败。"""

    settings = get_settings()
    normalized_username = username.strip().lower()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            key = _login_failure_key(normalized_username)
            attempts = client.incr(key)
            if attempts == 1:
                client.expire(key, settings.login_failure_window_seconds)
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法记录登录失败") from exc

    _clear_expired_login_failures()
    count, reset_at = _login_failures.get(normalized_username, (0, _utc_now()))
    now = _utc_now()
    if reset_at <= now:
        count = 0
        reset_at = now + timedelta(seconds=settings.login_failure_window_seconds)
    _login_failures[normalized_username] = (count + 1, reset_at)


def clear_login_failures(username: str) -> None:
    """登录成功后清理失败计数。"""

    settings = get_settings()
    normalized_username = username.strip().lower()
    if redis_client.redis_is_configured(settings):
        try:
            client = redis_client.get_redis_client(settings)
            if client is None:
                raise redis_client.RedisUnavailableError("redis client is not configured")
            client.delete(_login_failure_key(normalized_username))
            return
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法清理登录限流") from exc

    _login_failures.pop(normalized_username, None)


def create_follow_up_stream_token(
    *,
    user_id: int,
    session_id: str,
    question_id: str,
    answer: str,
    expires_delta: timedelta | None = None,
) -> str:
    """生成仅用于追问 SSE 连接的短期 Token。"""

    settings = get_settings()
    token_expires_delta = expires_delta or timedelta(minutes=settings.stream_token_expire_minutes)
    payload = {
        "purpose": FOLLOW_UP_STREAM_PURPOSE,
        "sub": user_id,
        "session_id": session_id,
        "question_id": question_id,
        "answer": answer,
    }
    if redis_client.redis_is_configured(settings):
        return _create_redis_follow_up_stream_token(payload, token_expires_delta)

    return create_access_token(payload, expires_delta=token_expires_delta)


def decode_follow_up_stream_token(token: str) -> dict[str, Any]:
    """解析并校验追问 SSE Token。"""

    settings = get_settings()
    if redis_client.redis_is_configured(settings):
        return _decode_redis_follow_up_stream_token(token)

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token") from exc

    return _validate_follow_up_stream_payload(payload)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 Bearer Token 解析当前用户。"""

    payload = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == payload["sub"]).first()
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


def require_any_role(*allowed_roles: str):
    """FastAPI 依赖工厂：允许多个角色访问同一企业后台能力。"""

    normalized_roles = set(allowed_roles)

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in normalized_roles:
            allowed = "、".join(sorted(normalized_roles))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"需要以下角色之一：{allowed}")
        return current_user

    return checker


def _create_jwt_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    settings = get_settings()
    to_encode = data.copy()
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    now = _utc_now()
    to_encode.update(
        {
            "exp": now + expires_delta,
            "iat": now,
            "jti": to_encode.get("jti") or secrets.token_urlsafe(24),
        }
    )
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_jwt_token(token: str, *, invalid_detail: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_detail) from exc


def _normalize_subject(payload: dict[str, Any], *, invalid_detail: str) -> None:
    try:
        payload["sub"] = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_detail) from exc


def _create_redis_follow_up_stream_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    ttl_seconds = int(expires_delta.total_seconds())
    token_id = secrets.token_urlsafe(32)
    if ttl_seconds <= 0:
        return token_id

    try:
        client = redis_client.get_redis_client()
        if client is None:
            raise redis_client.RedisUnavailableError("redis client is not configured")
        client.setex(
            _stream_token_key(token_id),
            ttl_seconds,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法创建流式 Token") from exc
    return token_id


def _decode_redis_follow_up_stream_token(token: str) -> dict[str, Any]:
    try:
        client = redis_client.get_redis_client()
        if client is None:
            raise redis_client.RedisUnavailableError("redis client is not configured")
        raw_payload = _consume_stream_token(client, _stream_token_key(token))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis 不可用，无法解析流式 Token") from exc

    if raw_payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token")

    try:
        payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token") from exc
    return _validate_follow_up_stream_payload(payload)


def _consume_stream_token(client: Any, key: str) -> str | None:
    getdel = getattr(client, "getdel", None)
    if callable(getdel):
        return getdel(key)

    raw_payload = client.get(key)
    if raw_payload is not None:
        client.delete(key)
    return raw_payload


def _validate_follow_up_stream_payload(payload: dict[str, Any]) -> dict[str, Any]:
    required_fields = {"purpose", "sub", "session_id", "question_id", "answer"}
    if payload.get("purpose") != FOLLOW_UP_STREAM_PURPOSE or not required_fields.issubset(payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token")
    _normalize_subject(payload, invalid_detail="无效的流式 Token")
    return payload


def _stream_token_key(token: str) -> str:
    return f"{STREAM_TOKEN_KEY_PREFIX}{token}"


def _blacklist_key(jti: str) -> str:
    return f"{JWT_BLACKLIST_KEY_PREFIX}{jti}"


def _login_failure_key(username: str) -> str:
    return f"{LOGIN_FAILURE_KEY_PREFIX}{username}"


def _token_ttl_seconds(payload: dict[str, Any]) -> int:
    exp = payload.get("exp")
    if exp is None:
        return 0
    if isinstance(exp, datetime):
        exp_timestamp = exp.timestamp()
    else:
        exp_timestamp = float(exp)
    return max(0, int(exp_timestamp - _utc_now().timestamp()))


def _clear_expired_blacklisted_tokens() -> None:
    now = _utc_now()
    expired = [jti for jti, expires_at in _blacklisted_tokens.items() if expires_at <= now]
    for jti in expired:
        _blacklisted_tokens.pop(jti, None)


def _clear_expired_login_failures() -> None:
    now = _utc_now()
    expired = [username for username, (_count, reset_at) in _login_failures.items() if reset_at <= now]
    for username in expired:
        _login_failures.pop(username, None)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

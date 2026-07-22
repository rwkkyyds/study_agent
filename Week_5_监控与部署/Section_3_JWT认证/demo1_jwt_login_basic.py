"""
demo1：JWT 登录与 Token 签发基础

这个文件只演示认证链路的第一段：
1. 用户提交用户名和密码
2. 后端用 bcrypt 校验密码
3. 校验成功后用 PyJWT 签发 access_token

运行方式：
    python demo1_jwt_login_basic.py
"""

from datetime import datetime, timedelta, timezone
import logging

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SECRET_KEY = "dev-secret-key-change-me-at-least-32-bytes"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=50)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


USERS_DB = {
    "admin": {
        "username": "admin",
        "password_hash": hash_password("admin123"),
        "role": "admin",
    },
    "alice": {
        "username": "alice",
        "password_hash": hash_password("alice123"),
        "role": "user",
    },
}


def create_access_token(username: str, role: str) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": username,  # 【sub】Subject，表示这个 Token 属于哪个用户
        "role": role,
        "exp": expire_at,  # 【exp】过期时间，PyJWT 验证时会自动检查
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


app = FastAPI(title="JWT Login Basic Demo")


@app.post("/logwin", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    try:
        user = USERS_DB.get(request.username)
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not verify_passord(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_access_token(username=user["username"], role=user["role"])
        logger.info("用户 %s 登录成功，已签发 JWT", request.username)
        return TokenResponse(
            access_token=token,
            expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("登录接口发生未知错误")
        raise HTTPException(status_code=500, detail="登录服务暂时不可用") from exc


def run_local_demo() -> None:
    client = TestClient(app)

    print("\n=== 场景1：正确账号密码登录 ===")
    response = client.post(
        "/login",
        json={"username": "admin", "password": "admin123"},
    )
    print("状态码:", response.status_code)
    print("响应:", response.json())

    print("\n=== 场景2：错误密码登录 ===")
    response = client.post(
        "/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    print("状态码:", response.status_code)
    print("响应:", response.json())


if __name__ == "__main__":
    run_local_demo()

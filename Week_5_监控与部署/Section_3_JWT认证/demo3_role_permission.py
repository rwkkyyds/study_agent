"""
demo3：JWT 角色权限控制

这个文件继续扩展：
1. /profile：登录用户可访问
2. /admin/reports：只有 admin 角色能访问
3. require_role 用来复用权限检查逻辑

启动服务：
    uvicorn demo3_role_permission:app --reload --port 8000
"""

from datetime import datetime, timedelta, timezone
from typing import Callable
import logging

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.testclient import TestClient
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SECRET_KEY = "dev-secret-key-change-me-at-least-32-bytes"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    username: str
    role: str


class ReportSummary(BaseModel):
    title: str
    total_users: int
    risk_level: str


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


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
    payload = {"sub": username, "role": role, "exp": expire_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserProfile:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role or username not in USERS_DB:
            raise credentials_error
        return UserProfile(username=username, role=role)
    except ExpiredSignatureError as exc:
        raise credentials_error from exc
    except InvalidTokenError as exc:
        raise credentials_error from exc


def require_role(required_role: str) -> Callable[[UserProfile], UserProfile]:
    def checker(
        current_user: UserProfile = Depends(get_current_user),
    ) -> UserProfile:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 权限",
            )
        return current_user

    return checker


app = FastAPI(title="JWT Role Permission Demo")


@app.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    try:
        user = USERS_DB.get(form.username)
        if not user or not verify_password(form.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_access_token(username=user["username"], role=user["role"])
        logger.info("用户 %s 登录成功，角色=%s", user["username"], user["role"])
        return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("登录接口发生未知错误")
        raise HTTPException(status_code=500, detail="登录服务暂时不可用") from exc


@app.get("/profile", response_model=UserProfile)
def read_profile(
    current_user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    return current_user


@app.get("/admin/reports", response_model=ReportSummary)
def read_admin_reports(
    admin_user: UserProfile = Depends(require_role("admin")),
) -> ReportSummary:
    logger.info("管理员 %s 查看运营报表", admin_user.username)
    return ReportSummary(
        title="AI Agent 平台运营报表",
        total_users=1280,
        risk_level="low",
    )


def login_and_get_token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/login",
        data={"username": username, "password": password},
    )
    return response.json()["access_token"]   


def run_local_demo() -> None:
    client = TestClient(app)

    alice_token = login_and_get_token(client, "alice", "alice123")
    admin_token = login_and_get_token(client, "admin", "admin123")

    print("\n=== 场景1：普通用户访问个人资料 ===")
    response = client.get(
        "/profile",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    print("状态码:", response.status_code)
    print("响应:", response.json())

    print("\n=== 场景2：普通用户访问管理员报表 ===")
    response = client.get(
        "/admin/reports",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    print("状态码:", response.status_code)
    print("响应:", response.json())

    print("\n=== 场景3：管理员访问管理员报表 ===")
    response = client.get(
        "/admin/reports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print("状态码:", response.status_code)
    print("响应:", response.json())


if __name__ == "__main__":
    run_local_demo()

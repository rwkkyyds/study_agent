"""
demo2：FastAPI 安全依赖与受保护接口

这个文件在 demo1 的基础上增加：
1. OAuth2PasswordBearer 从请求头提取 Bearer Token
2. get_current_user 解析 JWT 并返回当前用户
3. /me 接口只有登录用户才能访问

启动服务：
    uvicorn demo2_security_dependency:app --reload --port 8000
"""

from datetime import datetime, timedelta, timezone
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

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login"
)  # 【tokenUrl】告诉 Swagger 登录拿 Token 的接口地址
# 【OAuth2PasswordBearer】只负责从 Authorization 请求头里提取 Bearer Token，
# 不会自动校验 JWT，真正的解析和验证要在 get_current_user 里完成。


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    username: str
    role: str


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
    payload = {
        "sub": username,  # 【sub】Subject，表示这个 Token 属于哪个用户
        "role": role,  # 【role】角色信息，后续可以用来做权限判断
        "exp": expire_at,  # 【exp】过期时间，PyJWT decode 时会自动校验
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)  # 用密钥签名，防止 Payload 被篡改


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserProfile:
    # 【Depends(oauth2_scheme)】先从请求头提取 token，再把 token 传给当前函数。
    # 请求头格式必须是：Authorization: Bearer <access_token>
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )  # 【WWW-Authenticate】告诉客户端这个接口需要 Bearer Token

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # 校验签名、算法和 exp 过期时间
        username = payload.get("sub")  # 从 Token 中取出用户名，而不是信任客户端单独传来的用户名
        role = payload.get("role")
        if not username or not role:
            raise credentials_error

        user = USERS_DB.get(username)  # 再查一次用户表，防止已删除用户继续拿旧 Token 访问
        if not user:
            raise credentials_error

        return UserProfile(username=username, role=role)  # 返回给接口层的“当前登录用户”
    except ExpiredSignatureError as exc:
        logger.warning("Token 已过期")
        raise credentials_error from exc
    except InvalidTokenError as exc:
        logger.warning("Token 解析失败")
        raise credentials_error from exc


app = FastAPI(title="FastAPI Security Dependency Demo")


@app.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    # 【OAuth2PasswordRequestForm】按 OAuth2 规范接收表单字段 username/password，
    # 所以测试或前端请求这里要用 form-data，而不是 JSON 请求体。
    try:
        user = USERS_DB.get(form.username)
        if not user or not verify_password(form.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_access_token(username=user["username"], role=user["role"])
        return TokenResponse(access_token=token)  # 客户端后续访问受保护接口时，要把它放进 Authorization 头
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("登录接口发生未知错误")
        raise HTTPException(status_code=500, detail="登录服务暂时不可用") from exc


@app.get("/me", response_model=UserProfile)
def read_me(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    # 只要接口依赖 get_current_user，FastAPI 就会在进入业务代码前先完成 Token 校验。
    return current_user


def run_local_demo() -> None:
    client = TestClient(app)

    print("\n=== 场景1：先登录获取 Token ===")
    login_response = client.post(
        "/login",
        data={"username": "alice", "password": "alice123"},  # 对应 OAuth2PasswordRequestForm 的表单格式
    )
    token = login_response.json()["access_token"]
    print("登录状态码:", login_response.status_code)

    print("\n=== 场景2：携带 Token 访问 /me ===")
    me_response = client.get("/me", headers={"Authorization": f"Bearer {token}"})  # Bearer 后面必须有一个空格
    print("状态码:", me_response.status_code)
    print("响应:", me_response.json())

    print("\n=== 场景3：不带 Token 访问 /me ===")
    no_token_response = client.get("/me")
    print("状态码:", no_token_response.status_code)
    print("响应:", no_token_response.json())


if __name__ == "__main__":
    run_local_demo()

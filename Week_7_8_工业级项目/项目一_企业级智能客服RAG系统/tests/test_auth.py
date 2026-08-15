"""第二阶段认证接口测试。"""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.auth import get_login_rate_limiter
from app.core.config import get_settings
from app.db.session import Base, get_db
from app.main import app
from app.stability.rate_limit import SlidingWindowRateLimiter

# 使用独立测试数据库，与 lifespan 的 init_db() 保持一致
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """测试用数据库会话，覆盖主应用的 get_db 依赖。"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试函数重建表，保证隔离。"""
    login_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_login_rate_limiter] = lambda: login_limiter
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)


class TestAuth:
    """认证接口测试集。"""

    REGISTER_URL = "/auth/register"
    LOGIN_URL = "/auth/login"
    ME_URL = "/auth/me"

    def test_register_success(self):
        """注册新用户成功，默认角色为 customer。"""
        response = client.post(self.REGISTER_URL, json={
            "username": "testuser",
            "password": "testpass123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "customer"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_register_duplicate_username(self):
        """重复用户名注册返回 400。"""
        client.post(self.REGISTER_URL, json={
            "username": "dupuser",
            "password": "testpass123",
        })
        response = client.post(self.REGISTER_URL, json={
            "username": "dupuser",
            "password": "testpass123",
        })
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    def test_login_success(self):
        """注册后登录成功返回 JWT。"""
        client.post(self.REGISTER_URL, json={
            "username": "loginuser",
            "password": "mypassword",
        })
        response = client.post(self.LOGIN_URL, json={
            "username": "loginuser",
            "password": "mypassword",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        """错误密码登录返回 401。"""
        client.post(self.REGISTER_URL, json={
            "username": "passuser",
            "password": "correctpass",
        })
        response = client.post(self.LOGIN_URL, json={
            "username": "passuser",
            "password": "wrongpass",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self):
        """不存在的用户登录返回 401。"""
        response = client.post(self.LOGIN_URL, json={
            "username": "nobody",
            "password": "somepass",
        })
        assert response.status_code == 401

    def test_get_me_with_token(self):
        """使用有效 Token 获取用户信息。"""
        client.post(self.REGISTER_URL, json={
            "username": "meuser",
            "password": "mepass",
        })
        login_resp = client.post(self.LOGIN_URL, json={
            "username": "meuser",
            "password": "mepass",
        })
        token = login_resp.json()["access_token"]

        response = client.get(self.ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "meuser"

    def test_get_me_without_token(self):
        """未提供 Token 访问 /auth/me 返回 401（HTTPBearer 默认行为）。"""
        response = client.get(self.ME_URL)
        assert response.status_code == 401

    def test_get_me_with_invalid_token(self):
        """无效 Token 访问 /auth/me 返回 401。"""
        response = client.get(self.ME_URL, headers={"Authorization": "Bearer invalidtoken123"})
        assert response.status_code == 401

    def test_get_me_with_token_missing_subject_returns_401(self):
        """签名合法但缺少 sub 的 Token 返回 401，而不是服务端 500。"""
        settings = get_settings()
        token = jwt.encode({"foo": "bar"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        response = client.get(self.ME_URL, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401

    def test_login_rate_limited_after_repeated_failures(self):
        """同一 IP 连续错误登录超过阈值后返回 429。"""
        client.post(self.REGISTER_URL, json={
            "username": "limituser",
            "password": "correctpass",
        })

        for _ in range(10):
            response = client.post(self.LOGIN_URL, json={
                "username": "limituser",
                "password": "wrongpass",
            })
            assert response.status_code == 401

        response = client.post(self.LOGIN_URL, json={
            "username": "limituser",
            "password": "wrongpass",
        })
        assert response.status_code == 429

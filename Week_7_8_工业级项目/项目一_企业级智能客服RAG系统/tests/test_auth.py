"""认证 API 测试：注册、登录、获取用户信息。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup_db():
    """每个测试前重建表，保证测试隔离。"""

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


class TestAuth:
    """认证接口测试集。"""

    REGISTER_URL = "/auth/register"
    LOGIN_URL = "/auth/login"
    ME_URL = "/auth/me"

    def test_register_success(self):
        """注册新用户应返回 201 和用户信息。"""

        payload = {"username": "testuser", "password": "test123456"}
        response = client.post(self.REGISTER_URL, json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "customer"
        assert "password" not in data  # 不返回密码

    def test_register_duplicate_username(self):
        """重复用户名应返回 409。"""

        payload = {"username": "dupuser", "password": "test123456"}
        client.post(self.REGISTER_URL, json=payload)
        response = client.post(self.REGISTER_URL, json=payload)

        assert response.status_code == 409

    def test_login_success(self):
        """登录成功应返回 JWT token。"""

        client.post(self.REGISTER_URL, json={"username": "loginuser", "password": "test123456"})
        response = client.post(self.LOGIN_URL, json={"username": "loginuser", "password": "test123456"})

        assert response.status_code == 200
        data = response.json()
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self):
        """密码错误应返回 401。"""

        client.post(self.REGISTER_URL, json={"username": "authuser", "password": "test123456"})
        response = client.post(self.LOGIN_URL, json={"username": "authuser", "password": "wrongpass"})

        assert response.status_code == 401

    def test_login_nonexistent_user(self):
        """不存在的用户登录应返回 401。"""

        response = client.post(self.LOGIN_URL, json={"username": "nobody", "password": "test123456"})

        assert response.status_code == 401

    def test_get_me_with_token(self):
        """携带有效 token 访问 /auth/me 应返回用户信息。"""

        client.post(self.REGISTER_URL, json={"username": "meuser", "password": "test123456"})
        login_resp = client.post(self.LOGIN_URL, json={"username": "meuser", "password": "test123456"})
        token = login_resp.json()["access_token"]

        response = client.get(self.ME_URL, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["username"] == "meuser"

    def test_get_me_without_token(self):
        """未携带 token 访问 /auth/me 应返回 401。"""

        response = client.get(self.ME_URL)
        assert response.status_code == 401

    def test_get_me_with_invalid_token(self):
        """无效 token 访问应返回 401。"""

        response = client.get(self.ME_URL, headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401
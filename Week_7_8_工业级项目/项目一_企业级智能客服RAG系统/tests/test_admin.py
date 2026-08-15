"""管理员用户管理接口测试（POST/GET /auth/users）。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth import get_current_user

# 使用独立的测试数据库
TEST_DATABASE_URL = "sqlite:///./test_admin.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试函数重建表，保证隔离。"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def _make_user_stub(user_id: int = 1, role: str = "customer"):
    """创建用户桩，用于覆盖 get_current_user 依赖。"""
    return type("UserStub", (), {"id": user_id, "role": role, "is_active": True})()


class TestAdminCreateUser:
    """管理员创建用户接口测试。"""

    URL = "/auth/users"

    def test_create_requires_admin(self):
        """customer 调用创建接口返回 403。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="customer")
        response = TestClient(app).post(self.URL, json={
            "username": "newagent",
            "password": "pass123",
            "role": "agent",
        })
        assert response.status_code == 403

    def test_agent_cannot_create_user(self):
        """agent 调用创建接口返回 403。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="agent")
        response = TestClient(app).post(self.URL, json={
            "username": "newagent",
            "password": "pass123",
            "role": "agent",
        })
        assert response.status_code == 403

    def test_admin_creates_agent_success(self):
        """admin 创建 agent 账号成功。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).post(self.URL, json={
            "username": "support01",
            "password": "pass123",
            "role": "agent",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "support01"
        assert data["role"] == "agent"
        assert data["is_active"] is True

    def test_admin_creates_admin_success(self):
        """admin 创建 admin 账号成功。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).post(self.URL, json={
            "username": "root02",
            "password": "pass123",
            "role": "admin",
        })
        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    def test_create_invalid_role_returns_422(self):
        """非法角色返回 422（角色必须在 admin/agent/customer 中）。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).post(self.URL, json={
            "username": "badrole",
            "password": "pass123",
            "role": "superuser",
        })
        assert response.status_code == 422

    def test_create_duplicate_username_returns_400(self):
        """重复用户名返回 400。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        client = TestClient(app)
        client.post(self.URL, json={
            "username": "dupuser",
            "password": "pass123",
            "role": "agent",
        })
        response = client.post(self.URL, json={
            "username": "dupuser",
            "password": "pass123",
            "role": "customer",
        })
        assert response.status_code == 400

    def test_created_user_can_login(self):
        """admin 创建的 agent 账号可用 /auth/login 正常登录。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        client = TestClient(app)
        client.post(self.URL, json={
            "username": "loginagent",
            "password": "pass123",
            "role": "agent",
        })
        # 恢复真实认证，验证登录
        app.dependency_overrides.pop(get_current_user, None)
        response = client.post("/auth/login", json={
            "username": "loginagent",
            "password": "pass123",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestAdminListUsers:
    """管理员用户列表接口测试。"""

    URL = "/auth/users"

    def test_list_requires_admin(self):
        """customer 调用列表接口返回 403。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="customer")
        response = TestClient(app).get(self.URL)
        assert response.status_code == 403

    def test_list_returns_all_users(self):
        """admin 可以查看全部用户（含不同角色）。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        client = TestClient(app)
        # 通过 admin 接口创建不同角色用户
        for username, role in [("alice", "customer"), ("bob", "agent"), ("carol", "admin")]:
            client.post(self.URL, json={
                "username": username,
                "password": "pass123",
                "role": role,
            })
        response = client.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        roles = {u["username"]: u["role"] for u in data}
        assert roles == {"alice": "customer", "bob": "agent", "carol": "admin"}

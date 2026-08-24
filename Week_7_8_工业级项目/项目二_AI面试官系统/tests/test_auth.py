from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.security import AuditLog
from app.models.user import User
from app.services.auth import create_user


def test_register_login_and_me(client, db_session: Session):
    register = client.post("/auth/register", json={"username": "candidate_auth", "password": "secret123"})
    assert register.status_code == 201
    assert register.json()["role"] == "candidate"

    login = client.post("/auth/login", json={"username": "candidate_auth", "password": "secret123"})
    assert login.status_code == 200
    login_data = login.json()
    token = login_data["access_token"]
    assert login_data["refresh_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "candidate_auth"

    actions = {
        log.action
        for log in db_session.query(AuditLog).filter_by(username="candidate_auth").order_by(AuditLog.id.asc()).all()
    }
    assert {"auth.register", "auth.login"}.issubset(actions)


def test_admin_can_create_and_list_users(client, db_session: Session):
    create_user(db_session, username="admin1", password="secret123", role="admin")
    login = client.post("/auth/login", json={"username": "admin1", "password": "secret123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post(
        "/auth/users",
        json={"username": "hr_admin_created", "password": "secret123", "role": "hr"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["role"] == "hr"

    listed = client.get("/auth/users", headers=headers)
    assert listed.status_code == 200
    assert {user["username"] for user in listed.json()} == {"admin1", "hr_admin_created"}
    assert db_session.query(User).count() == 2


def test_refresh_rotates_refresh_token(client):
    client.post("/auth/register", json={"username": "refresh_user", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "refresh_user", "password": "secret123"})
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert refreshed.status_code == 200
    refreshed_data = refreshed.json()
    assert refreshed_data["access_token"]
    assert refreshed_data["refresh_token"]
    assert refreshed_data["refresh_token"] != refresh_token

    replay = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401


def test_logout_blacklists_access_and_refresh_token(client):
    client.post("/auth/register", json={"username": "logout_user", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "logout_user", "password": "secret123"})
    token_data = login.json()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    logout = client.post("/auth/logout", json={"refresh_token": token_data["refresh_token"]}, headers=headers)

    assert logout.status_code == 200
    assert logout.json()["message"] == "已退出登录"
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": token_data["refresh_token"]}).status_code == 401


def test_login_failed_attempts_are_rate_limited(monkeypatch, client, db_session: Session):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("LOGIN_FAILURE_LIMIT", "2")
    monkeypatch.setenv("LOGIN_FAILURE_WINDOW_SECONDS", "60")
    get_settings.cache_clear()

    try:
        for _ in range(2):
            response = client.post("/auth/login", json={"username": "limited_user", "password": "bad-secret"})
            assert response.status_code == 401

        blocked = client.post("/auth/login", json={"username": "limited_user", "password": "bad-secret"})
    finally:
        get_settings.cache_clear()

    assert blocked.status_code == 429
    blocked_log = db_session.query(AuditLog).filter_by(username="limited_user", status="blocked").one()
    assert blocked_log.action == "auth.login"

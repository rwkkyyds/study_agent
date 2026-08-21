from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth import create_user


def test_register_login_and_me(client):
    register = client.post("/auth/register", json={"username": "candidate_auth", "password": "secret123"})
    assert register.status_code == 201
    assert register.json()["role"] == "candidate"

    login = client.post("/auth/login", json={"username": "candidate_auth", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "candidate_auth"


def test_admin_can_create_and_list_users(client, db_session: Session):
    create_user(db_session, username="admin1", password="secret123", role="admin")
    login = client.post("/auth/login", json={"username": "admin1", "password": "secret123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post(
        "/auth/users",
        json={"username": "candidate_admin_created", "password": "secret123", "role": "candidate"},
        headers=headers,
    )
    assert created.status_code == 201

    listed = client.get("/auth/users", headers=headers)
    assert listed.status_code == 200
    assert {user["username"] for user in listed.json()} == {"admin1", "candidate_admin_created"}
    assert db_session.query(User).count() == 2

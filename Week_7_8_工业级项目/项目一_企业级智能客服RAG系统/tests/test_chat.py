"""阶段四 Chat API 测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app
from app.services.auth import get_current_user


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: type(
        "UserStub", (), {"id": 1, "role": "customer"}
    )()
    yield TestClient(app)
    app.dependency_overrides.clear()
    db.close()


def test_chat_requires_authentication():
    app.dependency_overrides.clear()
    response = TestClient(app).post("/chat", json={"query": "退款规则是什么"})

    assert response.status_code == 401


def test_chat_knowledge_route(client):
    response = client.post("/chat", json={"query": "退款规则是什么"})

    assert response.status_code == 200
    assert response.json()["intent"] == "knowledge"
    assert "answer" in response.json()


def test_chat_stream_returns_sse_events(client):
    with client.stream("POST", "/chat/stream", json={"query": "退款规则是什么"}) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: chat.started" in body
    assert "event: chat.metadata" in body
    assert "event: chat.delta" in body
    assert "event: chat.done" in body


def test_chat_validates_blank_query(client):
    response = client.post("/chat", json={"query": ""})

    assert response.status_code == 422


def test_chat_forbids_agent_role():
    app.dependency_overrides[get_current_user] = lambda: type(
        "UserStub", (), {"id": 7, "role": "agent"}
    )()

    response = TestClient(app).post("/chat", json={"query": "请转人工"})

    assert response.status_code == 403
    assert response.json()["detail"] == "客服/管理员请使用客服工作台处理用户会话"
    app.dependency_overrides.clear()

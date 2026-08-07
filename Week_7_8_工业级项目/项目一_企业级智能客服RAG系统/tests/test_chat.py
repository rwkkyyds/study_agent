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


def test_chat_validates_blank_query(client):
    response = client.post("/chat", json={"query": ""})

    assert response.status_code == 422

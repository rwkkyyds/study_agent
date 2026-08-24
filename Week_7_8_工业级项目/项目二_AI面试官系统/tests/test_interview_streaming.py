from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.interview import InterviewFollowUp, InterviewSession
from app.services.auth import create_access_token, create_follow_up_stream_token, decode_follow_up_stream_token


RESUME_TEXT = "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。"


def _create_session(client, auth_headers) -> dict:
    response = client.post(
        "/interviews/questions",
        json={
            "resume_text": RESUME_TEXT,
            "job_title": "AI 应用开发工程师",
            "difficulty": "mid",
            "question_count": 5,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()


def test_stream_token_requires_authentication(client):
    response = client.post(
        "/interviews/follow-up/stream-token",
        json={
            "session_id": "missing",
            "question_id": "q1",
            "answer": "未登录不能创建流式 token。",
        },
    )

    assert response.status_code == 401


def test_current_user_can_create_stream_token(client, auth_headers):
    generated = _create_session(client, auth_headers)

    response = client.post(
        "/interviews/follow-up/stream-token",
        json={
            "session_id": generated["session_id"],
            "question_id": "q1",
            "answer": "我做了 RAG 检索和流式响应。",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["stream_token"]
    assert data["expires_in"] == 300


def test_redis_stream_token_hides_answer_and_is_single_use(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.store = {}
            self.ttls = {}

        def setex(self, key, ttl, value):
            self.store[key] = value
            self.ttls[key] = ttl

        def getdel(self, key):
            return self.store.pop(key, None)

    fake_redis = FakeRedis()
    answer = "这里是不能暴露在 URL Token 里的候选人敏感回答。"
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.auth.redis_client.get_redis_client", lambda settings=None: fake_redis)

    try:
        token = create_follow_up_stream_token(
            user_id=1,
            session_id="session-redis",
            question_id="q1",
            answer=answer,
        )
        assert answer not in token
        assert len(fake_redis.store) == 1

        payload = decode_follow_up_stream_token(token)

        assert payload["sub"] == 1
        assert payload["session_id"] == "session-redis"
        assert payload["question_id"] == "q1"
        assert payload["answer"] == answer
        assert fake_redis.store == {}

        with pytest.raises(HTTPException) as exc:
            decode_follow_up_stream_token(token)
    finally:
        get_settings.cache_clear()

    assert exc.value.status_code == 401


def test_other_user_cannot_create_stream_token_for_session(client, auth_headers):
    generated = _create_session(client, auth_headers)
    client.post("/auth/register", json={"username": "stream_other", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "stream_other", "password": "secret123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        "/interviews/follow-up/stream-token",
        json={
            "session_id": generated["session_id"],
            "question_id": "q1",
            "answer": "尝试访问其他用户的会话。",
        },
        headers=other_headers,
    )

    assert response.status_code == 404


def test_follow_up_stream_returns_events_and_persists(client, auth_headers, db_session: Session):
    generated = _create_session(client, auth_headers)
    token_response = client.post(
        "/interviews/follow-up/stream-token",
        json={
            "session_id": generated["session_id"],
            "question_id": "q1",
            "answer": "我做了 RAG 项目，但还需要展开技术细节。",
        },
        headers=auth_headers,
    )
    token = token_response.json()["stream_token"]

    response = client.get(f"/interviews/follow-up/stream?token={token}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: trace" in body
    assert "event: follow_up" in body
    assert "event: done" in body

    session = db_session.query(InterviewSession).filter_by(session_id=generated["session_id"]).one()
    assert session.status == "running"
    saved = db_session.query(InterviewFollowUp).filter_by(session_db_id=session.id).one()
    assert saved.question_id == "q1"
    assert saved.follow_up_questions


def test_invalid_stream_token_returns_401(client):
    response = client.get("/interviews/follow-up/stream?token=not-a-valid-token")

    assert response.status_code == 401


def test_wrong_purpose_stream_token_returns_401(client, auth_headers, db_session: Session):
    generated = _create_session(client, auth_headers)
    session = db_session.query(InterviewSession).filter_by(session_id=generated["session_id"]).one()
    token = create_access_token(
        {
            "purpose": "access",
            "sub": session.user_id,
            "session_id": generated["session_id"],
            "question_id": "q1",
            "answer": "用途不匹配。",
        }
    )

    response = client.get(f"/interviews/follow-up/stream?token={token}")

    assert response.status_code == 401


def test_expired_stream_token_returns_401(client, auth_headers, db_session: Session):
    generated = _create_session(client, auth_headers)
    session = db_session.query(InterviewSession).filter_by(session_id=generated["session_id"]).one()
    token = create_follow_up_stream_token(
        user_id=session.user_id,
        session_id=generated["session_id"],
        question_id="q1",
        answer="过期 token。",
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(f"/interviews/follow-up/stream?token={token}")

    assert response.status_code == 401

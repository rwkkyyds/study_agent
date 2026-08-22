RESUME_TEXT = "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。"


def _create_session(client, auth_headers):
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


def _other_headers(client):
    client.post("/auth/register", json={"username": "sessions_other", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "sessions_other", "password": "secret123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_sessions_requires_authentication(client):
    response = client.get("/interviews/sessions")

    assert response.status_code == 401


def test_current_user_only_sees_own_sessions(client, auth_headers):
    generated = _create_session(client, auth_headers)
    other_headers = _other_headers(client)
    _create_session(client, other_headers)

    response = client.get("/interviews/sessions", headers=auth_headers)

    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert [session["session_id"] for session in sessions] == [generated["session_id"]]
    assert sessions[0]["question_count"] == 5
    assert sessions[0]["answer_count"] == 0
    assert sessions[0]["follow_up_count"] == 0
    assert sessions[0]["overall_score"] is None
    assert sessions[0]["level"] is None


def test_session_detail_returns_questions_answers_follow_ups_and_report(client, auth_headers):
    generated = _create_session(client, auth_headers)
    follow_up = client.post(
        "/interviews/follow-up",
        json={
            "session_id": generated["session_id"],
            "question_id": "q1",
            "answer": "我做了 RAG 检索和流式响应，但需要继续补充指标。",
        },
        headers=auth_headers,
    )
    assert follow_up.status_code == 200

    evaluated = client.post(
        "/interviews/evaluate",
        json={
            "session_id": generated["session_id"],
            "job_title": "AI 应用开发工程师",
            "answers": [
                {
                    "question_id": "q1",
                    "answer": "我会先说明业务目标，再说明 RAG 检索、缓存、数据库和部署监控。",
                }
            ],
        },
        headers=auth_headers,
    )
    assert evaluated.status_code == 200

    response = client.get(f"/interviews/sessions/{generated['session_id']}", headers=auth_headers)

    assert response.status_code == 200
    detail = response.json()
    assert detail["session_id"] == generated["session_id"]
    assert len(detail["questions"]) == 5
    assert len(detail["answers"]) == 1
    assert len(detail["follow_ups"]) == 1
    assert detail["report"]["overall_score"] == evaluated.json()["overall_score"]
    assert detail["overall_score"] == evaluated.json()["overall_score"]
    assert detail["level"] == evaluated.json()["level"]


def test_other_user_cannot_read_session_detail(client, auth_headers):
    generated = _create_session(client, auth_headers)
    other_headers = _other_headers(client)

    response = client.get(f"/interviews/sessions/{generated['session_id']}", headers=other_headers)

    assert response.status_code == 404

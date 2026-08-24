RESUME_TEXT = "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。"

from app.services.interview_drafts import clear_local_interview_drafts
from app.services.interview_tasks import clear_local_interview_tasks


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
    assert detail["report"]["visibility"] == "candidate"
    assert detail["report"]["dimensions"] == []
    assert detail["report"]["risks"] == []
    assert detail["overall_score"] == evaluated.json()["overall_score"]
    assert detail["level"] == evaluated.json()["level"]


def test_other_user_cannot_read_session_detail(client, auth_headers):
    generated = _create_session(client, auth_headers)
    other_headers = _other_headers(client)

    response = client.get(f"/interviews/sessions/{generated['session_id']}", headers=other_headers)

    assert response.status_code == 404


def test_interview_drafts_can_be_saved_restored_deleted_and_cleared(client, auth_headers):
    clear_local_interview_drafts()
    generated = _create_session(client, auth_headers)
    session_id = generated["session_id"]

    saved = client.put(
        f"/interviews/sessions/{session_id}/drafts",
        json={"question_id": "q1", "answer": "这是尚未最终提交的 Redis 草稿回答。"},
        headers=auth_headers,
    )
    assert saved.status_code == 200
    assert saved.json()["answer"] == "这是尚未最终提交的 Redis 草稿回答。"

    restored = client.get(f"/interviews/sessions/{session_id}/drafts", headers=auth_headers)
    assert restored.status_code == 200
    assert restored.json()["drafts"] == [
        {
            "session_id": session_id,
            "question_id": "q1",
            "answer": "这是尚未最终提交的 Redis 草稿回答。",
            "expires_in": restored.json()["expires_in"],
        }
    ]

    invalid_question = client.put(
        f"/interviews/sessions/{session_id}/drafts",
        json={"question_id": "missing", "answer": "不属于本会话的题目。"},
        headers=auth_headers,
    )
    assert invalid_question.status_code == 422

    other_headers = _other_headers(client)
    forbidden = client.get(f"/interviews/sessions/{session_id}/drafts", headers=other_headers)
    assert forbidden.status_code == 404

    deleted = client.delete(f"/interviews/sessions/{session_id}/drafts/q1", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get(f"/interviews/sessions/{session_id}/drafts", headers=auth_headers).json()["drafts"] == []

    client.put(
        f"/interviews/sessions/{session_id}/drafts",
        json={"question_id": "q1", "answer": "评分前保留的草稿。"},
        headers=auth_headers,
    )
    evaluated = client.post(
        "/interviews/evaluate",
        json={
            "session_id": session_id,
            "job_title": "AI 应用开发工程师",
            "answers": [{"question_id": "q1", "answer": "正式提交回答，生成报告后草稿应清空。"}],
        },
        headers=auth_headers,
    )
    assert evaluated.status_code == 200
    assert client.get(f"/interviews/sessions/{session_id}/drafts", headers=auth_headers).json()["drafts"] == []


def test_async_evaluate_task_can_be_polled_and_is_user_scoped(client, auth_headers):
    clear_local_interview_tasks()
    generated = _create_session(client, auth_headers)
    response = client.post(
        "/interviews/evaluate/async",
        json={
            "session_id": generated["session_id"],
            "job_title": "AI 应用开发工程师",
            "answers": [{"question_id": "q1", "answer": "我会说明 RAG、Redis、PostgreSQL、Docker、监控和降级。"}],
        },
        headers=auth_headers,
    )

    assert response.status_code == 202
    task_id = response.json()["task_id"]

    polled = client.get(f"/interviews/tasks/{task_id}", headers=auth_headers)
    assert polled.status_code == 200
    task = polled.json()
    assert task["task_type"] == "interview.report"
    assert task["session_id"] == generated["session_id"]
    assert task["status"] == "succeeded"
    assert task["result"]["visibility"] == "candidate"
    assert task["result"]["dimensions"] == []

    other_headers = _other_headers(client)
    forbidden = client.get(f"/interviews/tasks/{task_id}", headers=other_headers)
    assert forbidden.status_code == 404

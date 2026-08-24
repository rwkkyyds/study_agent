from sqlalchemy.orm import Session

from app.models.interview import InterviewFollowUp, InterviewSession


def test_generate_questions_returns_workflow_trace(client, auth_headers):
    response = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_trace"] == ["resume_parse_node", "job_profile_node", "rag_retrieval_node", "question_generation_node"]
    assert any(question["question_type"] == "job_profile" for question in data["questions"])


def test_follow_up_generates_and_persists(client, auth_headers, db_session: Session):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    response = client.post("/interviews/follow-up", json={
        "session_id": generated["session_id"],
        "question_id": "q1",
        "answer": "我做了一个 RAG 项目，但细节还没有展开。",
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == generated["session_id"]
    assert data["follow_up_questions"]
    assert "answer_analysis_node" in data["workflow_trace"]
    assert "follow_up_node" in data["workflow_trace"]

    session = db_session.query(InterviewSession).filter_by(session_id=generated["session_id"]).one()
    assert session.status == "follow_up_generated"
    saved = db_session.query(InterviewFollowUp).filter_by(session_db_id=session.id).one()
    assert saved.question_id == "q1"
    assert saved.follow_up_questions == data["follow_up_questions"]


def test_follow_up_rejects_other_users_session(client, auth_headers):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    client.post("/auth/register", json={"username": "followup_other", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "followup_other", "password": "secret123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post("/interviews/follow-up", json={
        "session_id": generated["session_id"],
        "question_id": "q1",
        "answer": "我想操作别人的会话。",
    }, headers=other_headers)

    assert response.status_code == 404


def test_follow_up_redirects_answer_that_does_not_address_question(client, auth_headers):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    response = client.post("/interviews/follow-up", json={
        "session_id": generated["session_id"],
        "question_id": "q1",
        "answer": "你好。",
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["follow_up_questions"]) == 1
    assert "还没有回应原题" in data["follow_up_questions"][0]
    assert "关联度较低" in data["reason"]


def test_follow_up_changes_with_relevant_answer(client, auth_headers):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    response = client.post("/interviews/follow-up", json={
        "session_id": generated["session_id"],
        "question_id": "q1",
        "answer": "我做过一个 RAG 项目，解决企业客服的业务问题。我负责 FastAPI、Milvus 检索和 Redis 缓存，项目上线后通过 Docker 部署和监控保障稳定性。",
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert 1 <= len(data["follow_up_questions"]) <= 2
    assert "还没有回应原题" not in data["follow_up_questions"][0]


def test_evaluate_report_returns_graph_trace(client, auth_headers):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    response = client.post("/interviews/evaluate", json={
        "session_id": generated["session_id"],
        "job_title": "AI 应用开发工程师",
        "answers": [{"question_id": "q1", "answer": "首先我会说明 RAG 项目的业务流程、Milvus 检索、Redis 缓存、Docker 部署、监控和降级策略。"}],
    }, headers=auth_headers)

    assert response.status_code == 200
    trace = response.json()["workflow_trace"]
    assert trace == ["answer_analysis_node", "follow_up_node", "scoring_node", "report_node"]


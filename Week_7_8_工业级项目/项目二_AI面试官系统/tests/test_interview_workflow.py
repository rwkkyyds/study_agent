from sqlalchemy.orm import Session

from app.models.interview import InterviewAnswer, InterviewQuestion, InterviewReport, InterviewSession


def test_generate_questions_from_resume(client, auth_headers, db_session: Session):
    response = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"].startswith("iv-")
    assert data["job_title"] == "AI 应用开发工程师"
    assert len(data["questions"]) == 5
    assert any(question["question_type"] == "rag" for question in data["questions"])

    session = db_session.query(InterviewSession).filter_by(session_id=data["session_id"]).one()
    assert session.job_title == "AI 应用开发工程师"
    assert len(session.questions) == 5


def test_generate_questions_requires_authentication(client):
    response = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 工程师",
    })

    assert response.status_code == 401


def test_generate_questions_validates_resume_length(client, auth_headers):
    response = client.post("/interviews/questions", json={
        "resume_text": "太短",
        "job_title": "AI 工程师",
    }, headers=auth_headers)

    assert response.status_code == 422


def test_evaluate_answers_returns_report_and_persists(client, auth_headers, db_session: Session):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    response = client.post("/interviews/evaluate", json={
        "session_id": generated["session_id"],
        "job_title": "AI 应用开发工程师",
        "answers": [
            {
                "question_id": "q1",
                "answer": "首先我会介绍项目业务，用户通过 RAG 知识库问答，后端使用 Milvus、Redis、PostgreSQL 和 Docker 部署，最后通过测试和监控保障稳定性。",
            }
        ],
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] >= 60
    assert data["visibility"] == "candidate"
    assert data["dimensions"] == []
    assert data["risks"] == []
    assert data["follow_up_questions"]

    session = db_session.query(InterviewSession).filter_by(session_id=generated["session_id"]).one()
    assert session.status == "evaluated"
    assert db_session.query(InterviewQuestion).filter_by(session_db_id=session.id).count() == 5
    assert db_session.query(InterviewAnswer).filter_by(session_db_id=session.id).count() == 1
    saved_report = db_session.query(InterviewReport).filter_by(session_db_id=session.id).one()
    assert saved_report.overall_score == data["overall_score"]
    assert len(saved_report.dimensions) == 4
    assert saved_report.risks


def test_evaluate_rejects_other_users_session(client, auth_headers):
    generated = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }, headers=auth_headers).json()

    client.post("/auth/register", json={"username": "candidate2", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "candidate2", "password": "secret123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post("/interviews/evaluate", json={
        "session_id": generated["session_id"],
        "job_title": "AI 应用开发工程师",
        "answers": [{"question_id": "q1", "answer": "首先说明项目业务和测试。"}],
    }, headers=other_headers)

    assert response.status_code == 404

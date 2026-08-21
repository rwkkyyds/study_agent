from sqlalchemy.orm import Session

from app.models.interview import InterviewSession
from app.models.resume import ResumeProfile


RESUME_TEXT = """
张三，AI 应用开发工程师，3 年项目经验。
项目一：企业级智能客服 RAG 系统，使用 Python、FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。
项目二：面试官 Agent 平台，负责后端 API、权限、测试和部署。
"""


def test_parse_text_resume_creates_profile(client, auth_headers, db_session: Session):
    response = client.post(
        "/resumes/parse",
        json={
            "content": RESUME_TEXT,
            "content_type": "text",
            "target_job_title": "AI 应用开发工程师",
            "source_name": "inline-resume.txt",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "text"
    assert "FastAPI" in data["skills"]
    assert "RAG" in data["skills"]
    assert data["years_of_experience"] == 3
    assert data["projects"]
    assert "岗位匹配关键词" in data["summary"]
    assert db_session.query(ResumeProfile).filter_by(id=data["id"]).one().source_name == "inline-resume.txt"


def test_upload_markdown_resume_creates_profile(client, auth_headers):
    markdown = """# 李四\n\n- 4 年后端经验\n- 项目：AI 面试官系统，使用 FastAPI、SQLAlchemy、Redis、Docker 和 RAG。\n"""

    response = client.post(
        "/resumes/upload",
        files={"file": ("resume.md", markdown.encode("utf-8"), "text/markdown")},
        data={"target_job_title": "AI 后端工程师"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "markdown"
    assert "FastAPI" in data["skills"]
    assert data["years_of_experience"] == 4
    assert "#" not in data["normalized_text"]


def test_resume_profile_is_user_scoped(client, auth_headers):
    created = client.post(
        "/resumes/parse",
        json={"content": RESUME_TEXT, "content_type": "text"},
        headers=auth_headers,
    ).json()

    client.post("/auth/register", json={"username": "resume_other", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "resume_other", "password": "secret123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(f"/resumes/{created['id']}", headers=other_headers)

    assert response.status_code == 404


def test_generate_questions_from_resume_profile(client, auth_headers, db_session: Session):
    profile = client.post(
        "/resumes/parse",
        json={
            "content": RESUME_TEXT,
            "content_type": "text",
            "target_job_title": "AI 应用开发工程师",
        },
        headers=auth_headers,
    ).json()

    response = client.post(
        "/interviews/questions",
        json={
            "resume_profile_id": profile["id"],
            "job_title": "AI 应用开发工程师",
            "difficulty": "mid",
            "question_count": 5,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert any(question["question_type"] == "rag" for question in data["questions"])
    session = db_session.query(InterviewSession).filter_by(session_id=data["session_id"]).one()
    assert session.resume_profile_id == profile["id"]

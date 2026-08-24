from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.hiring import CandidateProfile, InterviewInvite, NotificationLog
from app.models.interview import InterviewSession
from app.models.security import AuditLog
from app.models.user import User
from app.services.auth import create_user
from app.services.rate_limit import clear_local_api_rate_limits

RESUME_TEXT = "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。"


def _login_as(client, db_session: Session, username: str, role: str) -> dict[str, str]:
    create_user(db_session, username=username, password="secret123", role=role)
    login = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_job(client, headers: dict[str, str]) -> dict:
    response = client.post(
        "/hiring/jobs",
        json={
            "title": "AI 应用开发工程师",
            "level": "mid",
            "department": "AI 平台部",
            "jd_text": "负责企业级 AI Agent 应用、RAG 检索、服务稳定性和工程化交付，要求熟悉 FastAPI、PostgreSQL 和 Redis。",
            "skill_requirements": ["FastAPI", "PostgreSQL", "Redis", "RAG"],
            "scoring_dimensions": [{"name": "工程能力", "weight": 0.4}],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_candidate(client, headers: dict[str, str]) -> dict:
    response = client.post(
        "/hiring/candidates",
        json={
            "full_name": "张三",
            "email": "zhangsan@example.com",
            "source": "campus",
            "tags": ["RAG", "后端"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_session(client, headers: dict[str, str]) -> dict:
    response = client.post(
        "/interviews/questions",
        json={
            "resume_text": RESUME_TEXT,
            "job_title": "AI 应用开发工程师",
            "difficulty": "mid",
            "question_count": 5,
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_candidate_cannot_manage_hiring_domain(client, auth_headers):
    response = client.post(
        "/hiring/jobs",
        json={
            "title": "AI 应用开发工程师",
            "level": "mid",
            "jd_text": "负责企业级 AI Agent 应用、RAG 检索、服务稳定性和工程化交付。",
        },
        headers=auth_headers,
    )

    assert response.status_code == 403


def test_hr_can_create_core_hiring_domain_records(client, db_session: Session):
    headers = _login_as(client, db_session, username="hr_domain", role="hr")
    job = _create_job(client, headers)
    candidate = _create_candidate(client, headers)

    batch = client.post(
        "/hiring/batches",
        json={"job_id": job["id"], "name": "2026 春招第一批", "status": "active"},
        headers=headers,
    )
    assert batch.status_code == 201

    rubric = client.post(
        "/hiring/rubrics",
        json={
            "job_id": job["id"],
            "version": "v1",
            "name": "AI 应用开发工程师评分标准",
            "dimensions": [{"name": "项目深度", "weight": 0.5}, {"name": "稳定性意识", "weight": 0.5}],
            "weights": {"项目深度": 0.5, "稳定性意识": 0.5},
        },
        headers=headers,
    )
    assert rubric.status_code == 201

    invite = client.post(
        "/hiring/invites",
        json={"job_id": job["id"], "candidate_profile_id": candidate["id"], "batch_id": batch.json()["id"]},
        headers=headers,
    )
    assert invite.status_code == 201
    invite_data = invite.json()
    assert invite_data["status"] == "invited"
    assert invite_data["invite_token"]

    public_invite = client.get(f"/hiring/invites/{invite_data['invite_token']}")
    assert public_invite.status_code == 200
    assert public_invite.json()["candidate_profile_id"] == candidate["id"]
    assert public_invite.json()["job_title"] == job["title"]
    assert public_invite.json()["candidate_name"] == candidate["full_name"]
    assert public_invite.json()["candidate_email_masked"] == "zh***@example.com"

    notification_logs = client.get("/hiring/notification-logs", headers=headers)
    assert notification_logs.status_code == 200
    assert notification_logs.json()[0]["status"] == "queued"
    assert db_session.query(NotificationLog).count() == 1

    actions = {log.action for log in db_session.query(AuditLog).all()}
    assert {
        "hiring.job.create",
        "hiring.candidate.create",
        "hiring.batch.create",
        "hiring.rubric.create",
        "hiring.invite.create",
    }.issubset(actions)


def test_candidate_can_start_interview_from_invite_context(client, db_session: Session):
    hr_headers = _login_as(client, db_session, username="hr_invite_flow", role="hr")
    job = _create_job(client, hr_headers)
    candidate = _create_candidate(client, hr_headers)
    batch = client.post(
        "/hiring/batches",
        json={"job_id": job["id"], "name": "2026 春招第二批", "status": "active"},
        headers=hr_headers,
    ).json()
    rubric = client.post(
        "/hiring/rubrics",
        json={
            "job_id": job["id"],
            "version": "v1",
            "name": "岗位默认评分标准",
            "dimensions": [{"name": "工程能力", "weight": 1.0}],
            "weights": {"工程能力": 1.0},
        },
        headers=hr_headers,
    ).json()
    invite = client.post(
        "/hiring/invites",
        json={"job_id": job["id"], "candidate_profile_id": candidate["id"], "batch_id": batch["id"]},
        headers=hr_headers,
    ).json()

    client.post("/auth/register", json={"username": "invited_candidate", "password": "secret123"})
    login = client.post("/auth/login", json={"username": "invited_candidate", "password": "secret123"})
    candidate_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    generated = client.post(
        "/interviews/questions",
        json={
            "invite_token": invite["invite_token"],
            "resume_text": RESUME_TEXT,
            "difficulty": "mid",
            "question_count": 5,
        },
        headers=candidate_headers,
    )

    assert generated.status_code == 200
    data = generated.json()
    assert data["job_title"] == job["title"]
    assert data["job_id"] == job["id"]
    assert data["candidate_profile_id"] == candidate["id"]
    assert data["interview_batch_id"] == batch["id"]
    assert data["invite_id"] == invite["id"]
    assert data["rubric_id"] == rubric["id"]

    session = db_session.query(InterviewSession).filter_by(session_id=data["session_id"]).one()
    assert session.status == "running"
    assert session.job_id == job["id"]
    assert session.candidate_profile_id == candidate["id"]
    assert session.interview_batch_id == batch["id"]
    assert session.invite_id == invite["id"]
    assert session.rubric_id == rubric["id"]

    saved_invite = db_session.get(InterviewInvite, invite["id"])
    assert saved_invite.status == "accepted"
    assert saved_invite.used_at is not None

    saved_candidate = db_session.get(CandidateProfile, candidate["id"])
    saved_user = db_session.query(User).filter_by(username="invited_candidate").one()
    assert saved_candidate.user_id == saved_user.id
    assert saved_candidate.status == "interviewing"

    duplicate = client.post(
        "/interviews/questions",
        json={
            "invite_token": invite["invite_token"],
            "resume_text": RESUME_TEXT,
            "difficulty": "mid",
            "question_count": 5,
        },
        headers=candidate_headers,
    )
    assert duplicate.status_code == 409


def test_interviewer_can_create_manual_review(client, db_session: Session, auth_headers):
    generated = _create_session(client, auth_headers)
    reviewer_headers = _login_as(client, db_session, username="interviewer_review", role="interviewer")

    response = client.post(
        "/hiring/manual-reviews",
        json={
            "session_id": generated["session_id"],
            "recommendation": "hire",
            "decision": "advance",
            "score_override": 82,
            "comments": "候选人能说明 RAG、Redis 和部署稳定性，建议进入下一轮。",
            "risk_flags": ["需要继续验证生产排障经验"],
        },
        headers=reviewer_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["recommendation"] == "hire"
    session = db_session.query(InterviewSession).filter_by(session_id=generated["session_id"]).one()
    assert session.status == "reviewed"

    listed = client.get(f"/hiring/manual-reviews?session_id={generated['session_id']}", headers=reviewer_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["score_override"] == 82


def test_bound_rubric_weights_are_applied_to_interview_report(client, db_session: Session, auth_headers):
    hr_headers = _login_as(client, db_session, username="hr_rubric_score", role="hr")
    job = _create_job(client, hr_headers)
    rubric = client.post(
        "/hiring/rubrics",
        json={
            "job_id": job["id"],
            "version": "weighted-v1",
            "name": "偏重风险意识的评分标准",
            "dimensions": [{"name": "技术能力", "weight": 0.2}, {"name": "风险意识", "weight": 0.8}],
            "weights": {"技术能力": 0.2, "风险意识": 0.8},
        },
        headers=hr_headers,
    )
    assert rubric.status_code == 201

    generated = client.post(
        "/interviews/questions",
        json={
            "job_id": job["id"],
            "rubric_id": rubric.json()["id"],
            "resume_text": RESUME_TEXT,
            "difficulty": "mid",
            "question_count": 5,
        },
        headers=auth_headers,
    )
    assert generated.status_code == 200
    generated_data = generated.json()
    assert generated_data["rubric_id"] == rubric.json()["id"]

    response = client.post(
        "/interviews/evaluate",
        json={
            "session_id": generated_data["session_id"],
            "job_title": generated_data["job_title"],
            "answers": [
                {
                    "question_id": "q1",
                    "answer": "首先这个项目使用 RAG、向量、Milvus、Redis、PostgreSQL、Docker 和 LangGraph。其次说明流程、原因、权衡和指标，也覆盖项目、业务、用户、权限、测试、部署和稳定性。",
                }
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 56
    assert data["visibility"] == "candidate"
    assert data["dimensions"] == []
    assert data["risks"] == []
    assert "rubric_weighting_node" in data["workflow_trace"]

    detail = client.get(f"/interviews/sessions/{generated_data['session_id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["report"]["overall_score"] == 56
    assert detail.json()["report"]["visibility"] == "candidate"
    assert detail.json()["report"]["dimensions"] == []

    forbidden = client.get(f"/hiring/interview-sessions/{generated_data['session_id']}/report", headers=auth_headers)
    assert forbidden.status_code == 403

    reviewer_headers = _login_as(client, db_session, username="interviewer_report", role="interviewer")
    internal = client.get(f"/hiring/interview-sessions/{generated_data['session_id']}/report", headers=reviewer_headers)
    assert internal.status_code == 200
    internal_data = internal.json()
    assert internal_data["visibility"] == "internal"
    assert internal_data["overall_score"] == 56
    assert [dimension["name"] for dimension in internal_data["dimensions"]] == ["技术能力", "风险意识"]
    assert internal_data["risks"]


def test_high_cost_interview_api_is_rate_limited(monkeypatch, client, auth_headers):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()
    clear_local_api_rate_limits()

    try:
        first = client.post(
            "/interviews/questions",
            json={
                "resume_text": RESUME_TEXT,
                "job_title": "AI 应用开发工程师",
                "difficulty": "mid",
                "question_count": 5,
            },
            headers=auth_headers,
        )
        second = client.post(
            "/interviews/questions",
            json={
                "resume_text": RESUME_TEXT,
                "job_title": "AI 应用开发工程师",
                "difficulty": "mid",
                "question_count": 5,
            },
            headers=auth_headers,
        )
    finally:
        clear_local_api_rate_limits()
        get_settings.cache_clear()

    assert first.status_code == 200
    assert second.status_code == 429

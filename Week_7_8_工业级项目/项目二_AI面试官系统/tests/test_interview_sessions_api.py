RESUME_TEXT = "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。"

from app.core.config import get_settings
from app.services.interview_drafts import clear_local_interview_drafts
from app.services.interview_tasks import clear_local_interview_tasks
from app.workers.interview_worker import run_once


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.queues = {}

    def exists(self, key):
        return key in self.values

    def get(self, key):
        return self.values.get(key)

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
        return len(keys)

    def scan_iter(self, match=None):
        if not match or not match.endswith("*"):
            yield from self.values
            return
        prefix = match[:-1]
        for key in list(self.values):
            if key.startswith(prefix):
                yield key

    def setex(self, key, ttl_seconds, value):
        self.values[key] = value
        return True

    def incr(self, key):
        next_value = int(self.values.get(key, 0)) + 1
        self.values[key] = str(next_value)
        return next_value

    def expire(self, key, ttl_seconds):
        return True

    def rpush(self, key, value):
        self.queues.setdefault(key, []).append(value)
        return len(self.queues[key])

    def blpop(self, key, timeout=0):
        queue = self.queues.get(key, [])
        if not queue:
            return None
        return key, queue.pop(0)


class DbSessionContext:
    def __init__(self, db_session):
        self.db_session = db_session

    def __enter__(self):
        return self.db_session

    def __exit__(self, exc_type, exc, traceback):
        return False


def _question_payload():
    return {
        "resume_text": RESUME_TEXT,
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 5,
    }


def _create_session(client, auth_headers):
    response = client.post(
        "/interviews/questions",
        json=_question_payload(),
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
    assert sessions[0]["status"] == "running"


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
    assert task["status"] == "succeeded", task
    assert task["result"]["visibility"] == "candidate"
    assert task["result"]["dimensions"] == []
    detail = client.get(f"/interviews/sessions/{generated['session_id']}", headers=auth_headers).json()
    assert detail["status"] == "ai_reported"

    other_headers = _other_headers(client)
    forbidden = client.get(f"/interviews/tasks/{task_id}", headers=other_headers)
    assert forbidden.status_code == 404


def test_async_evaluate_can_run_through_redis_worker_queue(monkeypatch, client, auth_headers, db_session):
    generated = _create_session(client, auth_headers)
    fake_redis = FakeRedis()

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("INTERVIEW_TASK_QUEUE_BACKEND", "redis")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.redis_client.get_redis_client", lambda settings=None: fake_redis)

    try:
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
        assert response.json()["status"] == "queued"
        assert fake_redis.queues["queue:interview_tasks"]

        assert run_once(timeout_seconds=0, db_factory=lambda: DbSessionContext(db_session)) is True

        polled = client.get(f"/interviews/tasks/{task_id}", headers=auth_headers)
        assert polled.status_code == 200
        task = polled.json()
        assert task["status"] == "succeeded", task
        assert task["result"]["visibility"] == "candidate"
        assert task["result"]["dimensions"] == []
        detail = client.get(f"/interviews/sessions/{generated['session_id']}", headers=auth_headers).json()
        assert detail["status"] == "ai_reported"
        assert fake_redis.queues["queue:interview_tasks"] == []
    finally:
        get_settings.cache_clear()


def test_async_follow_up_task_can_be_polled_with_background_fallback(client, auth_headers):
    clear_local_interview_tasks()
    generated = _create_session(client, auth_headers)
    response = client.post(
        "/interviews/follow-up/async",
        json={
            "session_id": generated["session_id"],
            "question_id": "q1",
            "answer": "我做了 RAG 检索和流式响应，但需要继续补充指标。",
        },
        headers=auth_headers,
    )

    assert response.status_code == 202
    assert response.json()["task_type"] == "interview.follow_up"
    task_id = response.json()["task_id"]

    polled = client.get(f"/interviews/tasks/{task_id}", headers=auth_headers)
    assert polled.status_code == 200
    task = polled.json()
    assert task["status"] == "succeeded", task
    assert task["session_id"] == generated["session_id"]
    assert task["result"]["session_id"] == generated["session_id"]
    assert task["result"]["follow_up_questions"]

    detail = client.get(f"/interviews/sessions/{generated['session_id']}", headers=auth_headers).json()
    assert detail["status"] == "running"
    assert detail["follow_up_count"] == 1


def test_async_follow_up_can_run_through_redis_worker_queue(monkeypatch, client, auth_headers, db_session):
    generated = _create_session(client, auth_headers)
    fake_redis = FakeRedis()

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("INTERVIEW_TASK_QUEUE_BACKEND", "redis")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.redis_client.get_redis_client", lambda settings=None: fake_redis)

    try:
        response = client.post(
            "/interviews/follow-up/async",
            json={
                "session_id": generated["session_id"],
                "question_id": "q1",
                "answer": "我做了 RAG 检索和流式响应，但需要继续补充指标。",
            },
            headers=auth_headers,
        )

        assert response.status_code == 202
        task_id = response.json()["task_id"]
        assert response.json()["status"] == "queued"
        assert response.json()["task_type"] == "interview.follow_up"
        assert fake_redis.queues["queue:interview_tasks"]

        assert run_once(timeout_seconds=0, db_factory=lambda: DbSessionContext(db_session)) is True

        polled = client.get(f"/interviews/tasks/{task_id}", headers=auth_headers)
        assert polled.status_code == 200
        task = polled.json()
        assert task["status"] == "succeeded", task
        assert task["result"]["follow_up_questions"]
        assert fake_redis.queues["queue:interview_tasks"] == []
    finally:
        get_settings.cache_clear()


def test_async_questions_task_can_be_polled_with_background_fallback(client, auth_headers):
    clear_local_interview_tasks()
    response = client.post(
        "/interviews/questions/async",
        json=_question_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 202
    assert response.json()["task_type"] == "interview.questions"
    task_id = response.json()["task_id"]

    polled = client.get(f"/interviews/tasks/{task_id}", headers=auth_headers)
    assert polled.status_code == 200
    task = polled.json()
    assert task["status"] == "succeeded", task
    assert task["task_type"] == "interview.questions"
    assert task["session_id"] == task["result"]["session_id"]
    assert len(task["result"]["questions"]) == 5

    sessions = client.get("/interviews/sessions", headers=auth_headers).json()["sessions"]
    assert [session["session_id"] for session in sessions] == [task["result"]["session_id"]]


def test_async_questions_can_run_through_redis_worker_queue(monkeypatch, client, auth_headers, db_session):
    fake_redis = FakeRedis()

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("INTERVIEW_TASK_QUEUE_BACKEND", "redis")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.redis_client.get_redis_client", lambda settings=None: fake_redis)

    try:
        response = client.post(
            "/interviews/questions/async",
            json=_question_payload(),
            headers=auth_headers,
        )

        assert response.status_code == 202
        task_id = response.json()["task_id"]
        assert response.json()["status"] == "queued"
        assert response.json()["session_id"] == ""
        assert fake_redis.queues["queue:interview_tasks"]

        assert run_once(timeout_seconds=0, db_factory=lambda: DbSessionContext(db_session)) is True

        polled = client.get(f"/interviews/tasks/{task_id}", headers=auth_headers)
        assert polled.status_code == 200
        task = polled.json()
        assert task["status"] == "succeeded", task
        assert task["task_type"] == "interview.questions"
        assert task["session_id"] == task["result"]["session_id"]
        assert len(task["result"]["questions"]) == 5
        assert fake_redis.queues["queue:interview_tasks"] == []
    finally:
        get_settings.cache_clear()

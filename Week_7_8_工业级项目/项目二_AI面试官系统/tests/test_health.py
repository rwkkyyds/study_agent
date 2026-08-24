from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


def test_health_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ai-interviewer-system"


def test_ready_ok(monkeypatch, client):
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_settings.cache_clear()
    try:
        response = client.get("/health/ready")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    data = response.json()
    dependencies = {dependency["name"]: dependency for dependency in data["dependencies"]}
    assert data["status"] == "ready"
    assert dependencies["database"]["status"] == "ready"
    assert dependencies["redis"]["status"] == "disabled"
    assert dependencies["qwen"]["name"] == "qwen"


def test_ready_returns_503_when_database_unavailable(client):
    class BrokenDb:
        def execute(self, statement):
            raise SQLAlchemyError("database down")

    def override_get_db():
        yield BrokenDb()

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["dependency"] == "database"


def test_ready_returns_503_when_redis_unavailable(monkeypatch, client):
    class BrokenRedis:
        def ping(self):
            raise RuntimeError("redis down")

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    monkeypatch.setattr("app.api.health.redis_client.get_redis_client", lambda settings=None: BrokenRedis())

    try:
        response = client.get("/health/ready")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["detail"]["dependency"] == "redis"

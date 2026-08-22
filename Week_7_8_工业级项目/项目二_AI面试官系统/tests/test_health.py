from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.main import app


def test_health_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ai-interviewer-system"


def test_ready_ok(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["dependencies"][0]["name"] == "database"
    assert response.json()["dependencies"][0]["status"] == "ready"
    assert response.json()["dependencies"][1]["name"] == "qwen"


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

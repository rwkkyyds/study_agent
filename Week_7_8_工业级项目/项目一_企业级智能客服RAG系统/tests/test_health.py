"""第一阶段应用基础接口测试。"""

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "dependencies" in response.json()


def test_health_live() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready_with_database() -> None:
    """开发环境 SQLite 可用时，就绪检查返回数据库可用。"""

    response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["database"] is True


def test_health_ready_reports_configured_redis_unavailable(monkeypatch) -> None:
    """配置了 Redis 但客户端不可用时，就绪检查返回 503。"""

    monkeypatch.setattr(main.settings, "redis_url", "redis://localhost:6379/0")
    monkeypatch.setattr(main, "_redis_client", None)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Redis 不可用"


def test_version() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"

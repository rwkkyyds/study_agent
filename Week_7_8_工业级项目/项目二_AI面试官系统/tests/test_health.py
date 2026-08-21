def test_health_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ai-interviewer-system"


def test_ready_ok(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"

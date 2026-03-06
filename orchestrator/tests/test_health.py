from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"ok", "degraded", "down"}


def test_health_no_auth_required(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200

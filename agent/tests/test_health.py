from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ok", "degraded", "down"}
    assert "checkedAt" in data


def test_health_no_auth_required(client: TestClient) -> None:
    """Health endpoint must be accessible without an API key."""
    resp = client.get("/health")
    assert resp.status_code == 200

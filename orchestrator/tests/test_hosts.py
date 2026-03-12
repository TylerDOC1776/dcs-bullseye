from fastapi.testclient import TestClient

from .conftest import HEADERS, _HOST_PAYLOAD


def test_list_hosts_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/hosts", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_host(client: TestClient) -> None:
    resp = client.post("/api/v1/hosts", headers=HEADERS, json=_HOST_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Host"
    assert data["agentUrl"] == "http://10.0.0.1:8787"
    assert "id" in data


def test_list_hosts_after_create(client: TestClient, host_id: str) -> None:
    resp = client.get("/api/v1/hosts", headers=HEADERS)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == host_id


def test_get_host(client: TestClient, host_id: str) -> None:
    resp = client.get(f"/api/v1/hosts/{host_id}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["id"] == host_id


def test_get_host_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/hosts/nonexistent", headers=HEADERS)
    assert resp.status_code == 404


def test_patch_host(client: TestClient, host_id: str) -> None:
    resp = client.patch(
        f"/api/v1/hosts/{host_id}",
        headers=HEADERS,
        json={"name": "Renamed Host"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Host"


def test_hosts_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/hosts").status_code == 403
    assert client.post("/api/v1/hosts", json=_HOST_PAYLOAD).status_code == 403

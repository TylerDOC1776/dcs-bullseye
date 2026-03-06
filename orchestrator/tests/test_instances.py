from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from .conftest import HEADERS, _INSTANCE_PAYLOAD


def test_list_instances_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/instances", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_instance(client: TestClient, host_id: str) -> None:
    payload = {**_INSTANCE_PAYLOAD, "hostId": host_id}
    resp = client.post("/api/v1/instances", headers=HEADERS, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["serviceName"] == "DCS-test"
    assert data["hostId"] == host_id
    assert "id" in data


def test_create_instance_unknown_host(client: TestClient) -> None:
    payload = {**_INSTANCE_PAYLOAD, "hostId": "bad-host-id"}
    resp = client.post("/api/v1/instances", headers=HEADERS, json=payload)
    assert resp.status_code == 404


def test_get_instance(client: TestClient, instance_id: str) -> None:
    resp = client.get(f"/api/v1/instances/{instance_id}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["id"] == instance_id


def test_get_instance_by_name(client: TestClient, instance_id: str) -> None:
    resp = client.get("/api/v1/instances/Test Server", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["id"] == instance_id


def test_get_instance_by_service_name(client: TestClient, instance_id: str) -> None:
    resp = client.get("/api/v1/instances/DCS-test", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["id"] == instance_id


def test_get_instance_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/instances/nope", headers=HEADERS)
    assert resp.status_code == 404


def test_instances_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/instances").status_code == 403


def test_list_missions_proxies_to_agent(
    client: TestClient, instance_id: str
) -> None:
    with patch(
        "orchestrator.api.routes.instances.AgentClient"
    ) as MockClient:
        mock_instance = AsyncMock()
        mock_instance.list_missions.return_value = ["goonfront.miz", "red_flag.miz"]
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            f"/api/v1/instances/{instance_id}/missions", headers=HEADERS
        )
    assert resp.status_code == 200
    assert resp.json() == {"items": ["goonfront.miz", "red_flag.miz"]}


def test_list_missions_agent_down_returns_empty(
    client: TestClient, instance_id: str
) -> None:
    with patch(
        "orchestrator.api.routes.instances.AgentClient"
    ) as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(side_effect=Exception("refused"))
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            f"/api/v1/instances/{instance_id}/missions", headers=HEADERS
        )
    assert resp.status_code == 200
    assert resp.json() == {"items": []}

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .conftest import HEADERS


def test_list_instances(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances", headers=HEADERS)
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) == 1
    inst = items[0]
    assert inst["instanceId"] == "DCS-test"
    assert inst["name"] == "Test Server"
    assert inst["status"] == "running"


def test_list_instances_requires_auth(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances")
    assert resp.status_code == 401


def test_get_instance_status(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances/DCS-test/status", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert "observedAt" in data


def test_get_instance_status_by_name(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances/Test Server/status", headers=HEADERS)
    assert resp.status_code == 200


def test_get_instance_status_not_found(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances/nonexistent/status", headers=HEADERS)
    assert resp.status_code == 404


def test_get_instance_status_stopped(client: TestClient, mock_ctrl) -> None:
    mock_ctrl.status.return_value = "SERVICE_STOPPED"
    resp = client.get("/agent/v1/instances/DCS-test/status", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"

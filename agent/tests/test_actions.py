"""
Tests for POST /agent/v1/instances/{id}/actions/{action}.

Background tasks are not awaited in these tests — we only verify the
synchronous response (202 JobAccepted) and that the job appears in the store.
"""

import pytest
from fastapi.testclient import TestClient

from .conftest import HEADERS


def _trigger(client: TestClient, action: str, body: dict | None = None) -> dict:
    resp = client.post(
        f"/agent/v1/instances/DCS-test/actions/{action}",
        headers=HEADERS,
        json=body,
    )
    return resp


def test_start_returns_202(client: TestClient) -> None:
    resp = _trigger(client, "start")
    assert resp.status_code == 202
    data = resp.json()
    assert "jobId" in data
    assert data["status"] == "queued"


def test_stop_returns_202(client: TestClient) -> None:
    assert _trigger(client, "stop").status_code == 202


def test_restart_returns_202(client: TestClient) -> None:
    assert _trigger(client, "restart").status_code == 202


def test_logs_bundle_returns_202(client: TestClient) -> None:
    assert _trigger(client, "logs_bundle").status_code == 202


def test_mission_load_returns_202(client: TestClient) -> None:
    resp = _trigger(client, "mission_load", body={"mission": "goonfront.miz"})
    assert resp.status_code == 202


def test_mission_load_requires_mission_body(client: TestClient) -> None:
    resp = _trigger(client, "mission_load", body={})
    assert resp.status_code == 400
    assert "mission" in resp.json()["detail"].lower()


def test_mission_load_missing_body(client: TestClient) -> None:
    resp = client.post(
        "/agent/v1/instances/DCS-test/actions/mission_load",
        headers=HEADERS,
    )
    assert resp.status_code == 400


def test_unknown_action_returns_400(client: TestClient) -> None:
    resp = _trigger(client, "explode")
    assert resp.status_code == 400


def test_update_action_unsupported(client: TestClient) -> None:
    resp = _trigger(client, "update")
    assert resp.status_code == 400


def test_action_requires_auth(client: TestClient) -> None:
    resp = client.post("/agent/v1/instances/DCS-test/actions/start")
    assert resp.status_code == 401


def test_action_unknown_instance(client: TestClient) -> None:
    resp = client.post(
        "/agent/v1/instances/nonexistent/actions/start", headers=HEADERS
    )
    assert resp.status_code == 404


def test_job_created_in_store(client: TestClient) -> None:
    resp = _trigger(client, "start")
    job_id = resp.json()["jobId"]
    job_resp = client.get(f"/agent/v1/jobs/{job_id}", headers=HEADERS)
    assert job_resp.status_code == 200
    assert job_resp.json()["id"] == job_id

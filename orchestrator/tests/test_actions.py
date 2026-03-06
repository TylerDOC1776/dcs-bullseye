"""
Tests for POST /api/v1/instances/{id}/actions/{action}.

AgentClient is mocked so no real agent is needed.  Background tasks
may not complete within the synchronous TestClient — we test only the
synchronous response (202 + jobId) and auth/validation behaviour.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from .conftest import HEADERS


def _patch_agent(accepted: dict | None = None):
    """Context manager that stubs AgentClient.trigger_action."""
    accepted = accepted or {"jobId": "agent-job-1", "status": "queued"}
    mock_instance = AsyncMock()
    mock_instance.trigger_action.return_value = accepted
    mock_instance.get_job.return_value = {"status": "succeeded", "result": {}}

    class _CM:
        async def __aenter__(self):
            return mock_instance

        async def __aexit__(self, *_):
            return False

    return patch("orchestrator.api.routes.actions.AgentClient", return_value=_CM())


def test_start_action(client: TestClient, instance_id: str) -> None:
    with _patch_agent():
        resp = client.post(
            f"/api/v1/instances/{instance_id}/actions/start", headers=HEADERS
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "jobId" in data
    assert data["status"] == "queued"


def test_stop_action(client: TestClient, instance_id: str) -> None:
    with _patch_agent():
        resp = client.post(
            f"/api/v1/instances/{instance_id}/actions/stop", headers=HEADERS
        )
    assert resp.status_code == 202


def test_restart_action(client: TestClient, instance_id: str) -> None:
    with _patch_agent():
        resp = client.post(
            f"/api/v1/instances/{instance_id}/actions/restart", headers=HEADERS
        )
    assert resp.status_code == 202


def test_mission_load_action(client: TestClient, instance_id: str) -> None:
    with _patch_agent():
        resp = client.post(
            f"/api/v1/instances/{instance_id}/actions/mission_load",
            headers=HEADERS,
            json={"mission": "goonfront.miz"},
        )
    assert resp.status_code == 202


def test_mission_load_missing_body(client: TestClient, instance_id: str) -> None:
    resp = client.post(
        f"/api/v1/instances/{instance_id}/actions/mission_load",
        headers=HEADERS,
    )
    assert resp.status_code == 400
    assert "mission" in resp.json()["detail"].lower()


def test_unsupported_action(client: TestClient, instance_id: str) -> None:
    resp = client.post(
        f"/api/v1/instances/{instance_id}/actions/update", headers=HEADERS
    )
    assert resp.status_code == 400


def test_unknown_action(client: TestClient, instance_id: str) -> None:
    resp = client.post(
        f"/api/v1/instances/{instance_id}/actions/nuke", headers=HEADERS
    )
    assert resp.status_code == 400


def test_action_unknown_instance(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/instances/nonexistent/actions/start", headers=HEADERS
    )
    assert resp.status_code == 404


def test_action_requires_auth(client: TestClient, instance_id: str) -> None:
    resp = client.post(f"/api/v1/instances/{instance_id}/actions/start")
    assert resp.status_code == 403


def test_job_created_and_retrievable(client: TestClient, instance_id: str) -> None:
    with _patch_agent():
        resp = client.post(
            f"/api/v1/instances/{instance_id}/actions/start", headers=HEADERS
        )
    job_id = resp.json()["jobId"]
    job_resp = client.get(f"/api/v1/jobs/{job_id}", headers=HEADERS)
    assert job_resp.status_code == 200
    assert job_resp.json()["id"] == job_id

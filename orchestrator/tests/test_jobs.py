from fastapi.testclient import TestClient

from .conftest import HEADERS
from .test_actions import _patch_agent


def _create_job(client: TestClient, instance_id: str, action: str = "start") -> str:
    with _patch_agent():
        resp = client.post(
            f"/api/v1/instances/{instance_id}/actions/{action}", headers=HEADERS
        )
    assert resp.status_code == 202
    return resp.json()["jobId"]


def test_list_jobs_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/jobs", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_jobs(client: TestClient, instance_id: str) -> None:
    _create_job(client, instance_id)
    resp = client.get("/api/v1/jobs", headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_job(client: TestClient, instance_id: str) -> None:
    job_id = _create_job(client, instance_id)
    resp = client.get(f"/api/v1/jobs/{job_id}", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert data["status"] in {"queued", "running", "succeeded", "failed"}


def test_get_job_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/jobs/nope", headers=HEADERS)
    assert resp.status_code == 404


def test_list_jobs_status_filter(client: TestClient, instance_id: str) -> None:
    _create_job(client, instance_id)
    resp = client.get("/api/v1/jobs?status=queued", headers=HEADERS)
    assert resp.status_code == 200
    # May or may not have results depending on task timing, but must not error
    assert isinstance(resp.json(), list)


def test_jobs_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/jobs").status_code == 403

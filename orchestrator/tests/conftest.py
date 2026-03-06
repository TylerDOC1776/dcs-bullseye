"""
Shared fixtures for orchestrator tests.

Uses a real aiosqlite DB in a temp file (TestClient drives the async lifespan).
AgentClient is patched at the module level where needed — see individual test
files for action tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orchestrator.config import OrchestratorConfig
from orchestrator.api.app import create_app

KEY = "test-key"
HEADERS = {"X-API-Key": KEY}

_HOST_PAYLOAD = {
    "name": "Test Host",
    "agentUrl": "http://10.0.0.1:8787",
    "agentApiKey": "agent-key",
    "tags": [],
}

_INSTANCE_PAYLOAD = {
    "hostId": None,  # filled at runtime
    "serviceName": "DCS-test",
    "name": "Test Server",
    "tags": [],
}


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    config = OrchestratorConfig(
        db_path=str(tmp_path / "test.db"),
        api_key=KEY,
    )
    app = create_app(config)
    with TestClient(app) as tc:
        yield tc


@pytest.fixture()
def host_id(client: TestClient) -> str:
    """Create a host and return its id."""
    resp = client.post("/api/v1/hosts", headers=HEADERS, json=_HOST_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def instance_id(client: TestClient, host_id: str) -> str:
    """Create an instance under the test host and return its id."""
    payload = {**_INSTANCE_PAYLOAD, "hostId": host_id}
    resp = client.post("/api/v1/instances", headers=HEADERS, json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]

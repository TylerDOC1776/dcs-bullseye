"""
Shared fixtures for agent tests.

The agent app is created with a mocked DcsController so no NSSM or DCS
installation is required. Auth is enabled with api_key="test-key".
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from agent.config import AgentConfig, InstanceConfig
from agent.api.app import create_app

KEY = "test-key"
HEADERS = {"X-API-Key": KEY}


@pytest.fixture()
def missions_dir(tmp_path: Path) -> Path:
    d = tmp_path / "Missions"
    d.mkdir()
    return d


@pytest.fixture()
def instance_cfg(missions_dir: Path) -> InstanceConfig:
    return InstanceConfig(
        name="Test Server",
        service_name="DCS-test",
        exe_path=r"C:\DCS\bin\DCS_server.exe",
        saved_games_key="DCS.test",
        log_path=str(missions_dir.parent / "Logs" / "dcs.log"),
        missions_dir=str(missions_dir),
    )


@pytest.fixture()
def config(instance_cfg: InstanceConfig) -> AgentConfig:
    return AgentConfig(instances=[instance_cfg], api_key=KEY)


_RUNTIME_INFO = {
    "status": "SERVICE_RUNNING",
    "pid": None,
    "started_at": None,
    "mission_started_at": None,
    "mission_name": None,
    "map": None,
    "player_count": 0,
    "players": [],
    "mission_time_seconds": None,
}


@pytest.fixture()
def mock_ctrl() -> MagicMock:
    ctrl = MagicMock()
    ctrl.status.return_value = "SERVICE_RUNNING"
    ctrl.runtime_info.return_value = dict(_RUNTIME_INFO)
    ctrl.start.return_value = None
    ctrl.stop.return_value = None
    ctrl.restart.return_value = None
    ctrl.tail_logs.return_value = ["line 1", "line 2"]
    ctrl.mission_load.return_value = r"C:\Missions\test.miz"
    return ctrl


@pytest.fixture()
def client(config: AgentConfig, mock_ctrl: MagicMock) -> TestClient:
    app = create_app(config)
    app.state.controller = mock_ctrl
    with TestClient(app) as tc:
        yield tc

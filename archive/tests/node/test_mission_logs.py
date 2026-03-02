import base64
from pathlib import Path

import pytest

from node.node_service.config import InstanceConfig, NodeConfig
from node.node_service.logs import bundle_logs
from node.node_service.missions import deploy_mission


def test_deploy_mission_from_base64(tmp_path):
    instance = InstanceConfig(
        name="Test",
        cmd_key="test",
        exe_path="C:/DCS/Test/bin/DCS_server.exe",
        log_path="C:/Logs/test.log",
        missions_dir=str(tmp_path / "missions"),
    )
    payload = base64.b64encode(b"mission-bytes").decode("utf-8")
    params = {"filename": "mission.miz", "content_b64": payload}
    target = deploy_mission(instance, params)
    assert target.exists()
    assert target.read_bytes() == b"mission-bytes"


def test_bundle_logs_writes_tail(tmp_path):
    log_path = tmp_path / "dcs.log"
    log_path.write_text("line1\nline2\nline3\n", encoding="utf-8")
    instance = InstanceConfig(
        name="Test",
        cmd_key="test",
        exe_path="",
        log_path=str(log_path),
    )
    config = NodeConfig(
        node_id="node",
        role="server",
        vps_endpoint="https://example.com",
        api_key="token",
        instances=[instance],
        log_bundle_dir=tmp_path / "bundles",
        log_bundle_max_lines=2,
    )
    bundle = bundle_logs(instance, config)
    assert bundle.exists()
    assert bundle.read_text(encoding="utf-8").strip() == "line2\nline3".strip()

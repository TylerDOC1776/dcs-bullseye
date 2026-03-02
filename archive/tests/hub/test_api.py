import base64
from pathlib import Path

from fastapi.testclient import TestClient

from hub.api import create_app
from hub.config import HubConfig, NodeEntry
from hub.store import CommandStore, LogStore, NodeStatusStore


def make_client(tmp_path: Path) -> TestClient:
    config = HubConfig(
        admin_token="admin-token",
        nodes={"node-1": NodeEntry(token="node-token")},
        data_dir=tmp_path,
    )
    store = CommandStore(tmp_path / "commands.json")
    status_store = NodeStatusStore(tmp_path / "status.json")
    log_store = LogStore(tmp_path / "log_files", tmp_path / "logs.json")
    app = create_app(config, store, status_store=status_store, log_store=log_store)
    return TestClient(app)


def test_enqueue_fetch_ack(tmp_path):
    client = make_client(tmp_path)
    # enqueue
    resp = client.post(
        "/api/commands",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "node_id": "node-1",
            "action": "restart",
            "instance": "alpha",
            "params": None,
        },
    )
    assert resp.status_code == 200
    cmd_id = resp.json()["command"]["id"]

    # Node fetch
    resp = client.get(
        "/api/nodes/node-1/commands",
        headers={"Authorization": "Bearer node-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["commands"][0]["id"] == cmd_id

    # Ack
    resp = client.post(
        f"/api/nodes/node-1/commands/{cmd_id}/ack",
        headers={"Authorization": "Bearer node-token"},
        json={"success": True, "message": "done"},
    )
    assert resp.status_code == 200
    assert resp.json()["command"]["status"] == "succeeded"


def test_heartbeat_flow(tmp_path):
    client = make_client(tmp_path)
    payload = {
        "status": "online",
        "version": "0.1.0",
        "instances": [
            {"cmd_key": "southern", "name": "Southern Watch", "running": True, "pids": [1234]}
        ],
    }
    resp = client.post(
        "/api/nodes/node-1/heartbeat",
        headers={"Authorization": "Bearer node-token"},
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()["heartbeat"]
    assert data["status"] == "online"
    assert data["instances"][0]["running"] is True

    resp = client.get(
        "/api/heartbeats",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    assert nodes[0]["node_id"] == "node-1"


def test_log_upload_and_download(tmp_path):
    client = make_client(tmp_path)
    payload = {
        "instance": "southern",
        "filename": "dcs.log",
        "command_id": "cmd-123",
        "content_b64": base64.b64encode(b"log data here").decode("ascii"),
    }
    resp = client.post(
        "/api/nodes/node-1/logs",
        headers={"Authorization": "Bearer node-token"},
        json=payload,
    )
    assert resp.status_code == 200
    log_id = resp.json()["log"]["id"]
    listing = client.get("/api/logs", headers={"Authorization": "Bearer admin-token"})
    assert listing.status_code == 200
    assert any(entry["id"] == log_id for entry in listing.json()["logs"])
    filtered = client.get(
        "/api/logs",
        headers={"Authorization": "Bearer admin-token"},
        params={"command_id": "cmd-123"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["logs"][0]["id"] == log_id

    download = client.get(f"/api/logs/{log_id}", headers={"Authorization": "Bearer admin-token"})
    assert download.status_code == 200
    assert download.content == b"log data here"

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from node.node_service.comm import Command, CommandEnvelope, HttpCommandClient, LocalCommandTransport


@pytest.mark.asyncio
async def test_local_command_transport(tmp_path):
    cmd_dir = tmp_path / "commands"
    cmd_dir.mkdir()
    cmd_file = cmd_dir / "restart.json"
    cmd_file.write_text(
        '{"id":"cmd-1","action":"restart","instance":"alpha","params":{"delay":5}}',
        encoding="utf-8",
    )

    transport = LocalCommandTransport(cmd_dir)
    envelopes = await transport.fetch_commands()
    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert envelope.command.action == "restart"
    await transport.acknowledge(envelope, success=True)
    assert not cmd_file.exists()
    assert (cmd_dir / "restart.done").exists()


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class DummySession:
    def __init__(self):
        self.last_get = None
        self.last_post = None

    def get(self, url, headers, timeout):
        self.last_get = (url, headers, timeout)
        return DummyResponse({"commands": [{"id": "cmd-9", "action": "start", "instance": "bravo"}]})

    def post(self, url, headers, json, timeout):
        self.last_post = (url, headers, json, timeout)
        return DummyResponse({})


@pytest.mark.asyncio
async def test_http_command_client_fetch_and_ack():
    session = DummySession()
    client = HttpCommandClient("https://api.example.com", "token", "node-1", session=session)

    envelopes = await client.fetch_commands()
    assert envelopes[0].command.instance == "bravo"
    await client.acknowledge(envelopes[0], success=False, message="failed")

    assert session.last_get[0].endswith("/api/nodes/node-1/commands")
    assert session.last_post[0].endswith("/api/nodes/node-1/commands/cmd-9/ack")
    assert session.last_post[2]["success"] is False


@pytest.mark.asyncio
async def test_http_command_client_send_heartbeat():
    session = DummySession()
    client = HttpCommandClient("https://api.example.com", "token", "node-1", session=session)
    await client.send_heartbeat({"status": "online", "instances": []})
    assert session.last_post[0].endswith("/api/nodes/node-1/heartbeat")


@pytest.mark.asyncio
async def test_http_command_client_upload_log_bundle(tmp_path):
    session = DummySession()
    client = HttpCommandClient("https://api.example.com", "token", "node-1", session=session)
    bundle = tmp_path / "logs.txt"
    bundle.write_text("hello logs", encoding="utf-8")
    await client.upload_log_bundle(bundle, "southern", "cmd-11")
    assert session.last_post[0].endswith("/api/nodes/node-1/logs")
    assert session.last_post[2]["filename"] == "logs.txt"
    assert session.last_post[2]["command_id"] == "cmd-11"

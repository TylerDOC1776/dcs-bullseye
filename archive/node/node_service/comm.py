"""
Command ingestion helpers for the node service.

Current implementation watches a local folder (commands dropped in JSON files).
Later this can be replaced with HTTPS/WebSocket transport without touching the
service loop.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncio
import base64
import requests

LOG = logging.getLogger("node_service.comm")


@dataclass
class Command:
    id: str
    action: str
    instance: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class CommandEnvelope:
    command: Command
    context: Any = None


class CommandTransport:
    """Protocol-like base for fetching/acknowledging commands."""

    async def fetch_commands(self) -> List[CommandEnvelope]:  # pragma: no cover - interface
        raise NotImplementedError

    async def acknowledge(
        self, envelope: CommandEnvelope, success: bool, message: Optional[str] = None
    ) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class LocalCommandTransport(CommandTransport):
    """
    Simple file-based queue transport.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    async def fetch_commands(self) -> List[CommandEnvelope]:
        return await asyncio.to_thread(self._read_files)

    def _read_files(self) -> List[CommandEnvelope]:
        envelopes: List[CommandEnvelope] = []
        for file_path in sorted(self.directory.glob("*.json")):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                cmd_id = data.get("id") or file_path.stem
                command = Command(
                    id=str(cmd_id),
                    action=str(data["action"]),
                    instance=str(data["instance"]),
                    params=data.get("params"),
                )
                envelopes.append(CommandEnvelope(command=command, context=file_path))
            except Exception as exc:  # noqa: BLE001
                LOG.error("Failed to parse command file %s: %s", file_path, exc)
                file_path.rename(file_path.with_suffix(".error"))
        return envelopes

    async def acknowledge(
        self, envelope: CommandEnvelope, success: bool, message: Optional[str] = None
    ) -> None:
        await asyncio.to_thread(self._mark_processed, envelope.context, success)

    def _mark_processed(self, file_path: Path, success: bool) -> None:
        target_suffix = ".done" if success else ".failed"
        try:
            file_path.rename(file_path.with_suffix(target_suffix))
        except FileExistsError:
            file_path.unlink(missing_ok=True)


class HttpCommandClient(CommandTransport):
    """
    HTTPS transport that polls the central VPS for commands and acknowledges completion.
    """

    def __init__(self, base_url: str, api_key: str, node_id: str, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.node_id = node_id
        self.session = session or requests.Session()

    async def fetch_commands(self) -> List[CommandEnvelope]:
        return await asyncio.to_thread(self._fetch_commands_sync)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Node-ID": self.node_id,
            "Content-Type": "application/json",
        }

    def _fetch_commands_sync(self) -> List[CommandEnvelope]:
        url = f"{self.base_url}/api/nodes/{self.node_id}/commands"
        resp = self.session.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        commands = []
        for entry in payload.get("commands", []):
            cmd = Command(
                id=str(entry["id"]),
                action=str(entry["action"]),
                instance=str(entry["instance"]),
                params=entry.get("params"),
            )
            commands.append(CommandEnvelope(command=cmd))
        return commands

    async def acknowledge(
        self, envelope: CommandEnvelope, success: bool, message: Optional[str] = None
    ) -> None:
        await asyncio.to_thread(self._ack_sync, envelope.command.id, success, message)

    def _ack_sync(self, command_id: str, success: bool, message: Optional[str]) -> None:
        url = f"{self.base_url}/api/nodes/{self.node_id}/commands/{command_id}/ack"
        body = {"success": success, "message": message}
        resp = self.session.post(url, headers=self._headers(), json=body, timeout=10)
        resp.raise_for_status()

    async def send_heartbeat(self, payload: Dict[str, Any]) -> None:
        await asyncio.to_thread(self._send_heartbeat_sync, payload)

    def _send_heartbeat_sync(self, payload: Dict[str, Any]) -> None:
        url = f"{self.base_url}/api/nodes/{self.node_id}/heartbeat"
        resp = self.session.post(url, headers=self._headers(), json=payload, timeout=10)
        resp.raise_for_status()

    async def upload_log_bundle(self, bundle_path: Path, instance: str, command_id: Optional[str]) -> Dict[str, Any]:
        return await asyncio.to_thread(self._upload_log_bundle_sync, bundle_path, instance, command_id)

    def _upload_log_bundle_sync(self, bundle_path: Path, instance: str, command_id: Optional[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/nodes/{self.node_id}/logs"
        content = base64.b64encode(bundle_path.read_bytes()).decode("ascii")
        body = {
            "instance": instance,
            "filename": bundle_path.name,
            "command_id": command_id,
            "content_b64": content,
        }
        resp = self.session.post(url, headers=self._headers(), json=body, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("log", {})

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class CommandRecord:
    id: str
    node_id: str
    action: str
    instance: str
    params: Optional[dict] = None
    status: str = "pending"
    message: Optional[str] = None
    created_at: str = datetime.now(timezone.utc).isoformat()
    completed_at: Optional[str] = None

    def to_api_dict(self) -> Dict:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "action": self.action,
            "instance": self.instance,
            "params": self.params,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class CommandStore:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._commands: Dict[str, CommandRecord] = {}
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        for entry in data:
            record = CommandRecord(**entry)
            self._commands[record.id] = record

    def _save(self):
        payload = [asdict(record) for record in self._commands.values()]
        self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def enqueue(self, node_id: str, action: str, instance: str, params: Optional[dict] = None) -> CommandRecord:
        with self._lock:
            command = CommandRecord(
                id=str(uuid4()),
                node_id=node_id,
                action=action,
                instance=instance,
                params=params,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._commands[command.id] = command
            self._save()
            return command

    def pending_for_node(self, node_id: str) -> List[CommandRecord]:
        with self._lock:
            return [
                record
                for record in self._commands.values()
                if record.node_id == node_id and record.status == "pending"
            ]

    def acknowledge(self, node_id: str, command_id: str, success: bool, message: Optional[str]) -> CommandRecord:
        with self._lock:
            record = self._commands.get(command_id)
            if not record or record.node_id != node_id:
                raise KeyError(f"Command '{command_id}' not found for node '{node_id}'")
            record.status = "succeeded" if success else "failed"
            record.message = message
            record.completed_at = datetime.now(timezone.utc).isoformat()
            self._save()
            return record

    def list_commands(self, node_id: Optional[str] = None) -> List[CommandRecord]:
        with self._lock:
            if node_id:
                return [record for record in self._commands.values() if record.node_id == node_id]
            return list(self._commands.values())


@dataclass
class NodeHeartbeatRecord:
    node_id: str
    status: str = "online"
    message: Optional[str] = None
    instances: List[Dict[str, Any]] = None  # type: ignore[assignment]
    version: Optional[str] = None
    last_seen: str = datetime.now(timezone.utc).isoformat()

    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "message": self.message,
            "instances": self.instances or [],
            "version": self.version,
            "last_seen": self.last_seen,
        }


class NodeStatusStore:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._heartbeats: Dict[str, NodeHeartbeatRecord] = {}
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        for entry in data:
            record = NodeHeartbeatRecord(**entry)
            self._heartbeats[record.node_id] = record

    def _save(self):
        payload = [asdict(record) for record in self._heartbeats.values()]
        self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def update(
        self,
        node_id: str,
        status: str,
        instances: Optional[List[Dict[str, Any]]] = None,
        message: Optional[str] = None,
        version: Optional[str] = None,
    ) -> NodeHeartbeatRecord:
        with self._lock:
            record = NodeHeartbeatRecord(
                node_id=node_id,
                status=status,
                instances=instances or [],
                message=message,
                version=version,
                last_seen=datetime.now(timezone.utc).isoformat(),
            )
            self._heartbeats[node_id] = record
            self._save()
            return record

    def list_statuses(self) -> List[NodeHeartbeatRecord]:
        with self._lock:
            return list(self._heartbeats.values())

    def get_status(self, node_id: str) -> Optional[NodeHeartbeatRecord]:
        with self._lock:
            return self._heartbeats.get(node_id)


@dataclass
class LogRecord:
    id: str
    node_id: str
    instance: str
    filename: str
    path: str
    size: int
    created_at: str
    command_id: Optional[str] = None

    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "instance": self.instance,
            "filename": self.filename,
            "size": self.size,
            "created_at": self.created_at,
            "command_id": self.command_id,
        }


class LogStore:
    def __init__(self, storage_dir: Path, metadata_path: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = metadata_path
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._logs: Dict[str, LogRecord] = {}
        self._load()

    def _load(self):
        if not self.metadata_path.exists():
            return
        data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        for entry in data:
            record = LogRecord(**entry)
            self._logs[record.id] = record

    def _save(self):
        payload = [asdict(record) for record in self._logs.values()]
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def create(self, node_id: str, instance: str, filename: str, content: bytes, command_id: Optional[str] = None) -> LogRecord:
        with self._lock:
            log_id = str(uuid4())
            safe_name = filename.replace("/", "_").replace("\\", "_")
            target = self.storage_dir / f"{log_id}_{safe_name}"
            target.write_bytes(content)
            record = LogRecord(
                id=log_id,
                node_id=node_id,
                instance=instance,
                filename=safe_name,
                path=str(target),
                size=target.stat().st_size,
                created_at=datetime.now(timezone.utc).isoformat(),
                command_id=command_id,
            )
            self._logs[log_id] = record
            self._save()
            return record

    def list_logs(self, node_id: Optional[str] = None, command_id: Optional[str] = None) -> List[LogRecord]:
        with self._lock:
            records = list(self._logs.values())
            if node_id:
                records = [record for record in records if record.node_id == node_id]
            if command_id:
                records = [record for record in records if record.command_id == command_id]
            return records

    def get(self, log_id: str) -> Optional[LogRecord]:
        with self._lock:
            return self._logs.get(log_id)

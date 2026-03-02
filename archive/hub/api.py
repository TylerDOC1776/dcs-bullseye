from __future__ import annotations

import base64
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import HubConfig
from .store import CommandRecord, CommandStore, LogStore, NodeStatusStore


class AdminCommandRequest(BaseModel):
    node_id: str
    action: str
    instance: str
    params: dict | None = None


class AckRequest(BaseModel):
    success: bool
    message: str | None = None


class InstanceHeartbeat(BaseModel):
    cmd_key: str
    name: str
    running: bool
    pids: list[int] | None = None


class HeartbeatRequest(BaseModel):
    status: str = "online"
    message: str | None = None
    instances: list[InstanceHeartbeat] = []
    version: str | None = None


class LogUploadRequest(BaseModel):
    instance: str
    filename: str
    content_b64: str
    command_id: str | None = None


def create_app(
    config: HubConfig,
    store: CommandStore,
    status_store: NodeStatusStore | None = None,
    log_store: LogStore | None = None,
) -> FastAPI:
    app = FastAPI(title="DCS Admin Hub API")
    hb_store = status_store or NodeStatusStore(config.data_dir / "status.json")
    logs = log_store or LogStore(config.data_dir / "log_files", config.data_dir / "logs.json")

    def get_admin_token(auth_header: str = Header(..., alias="Authorization")) -> None:
        token = _parse_bearer(auth_header)
        if token != config.admin_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
        return None

    def get_node_auth(
        node_id: str,
        auth_header: str = Header(..., alias="Authorization"),
    ) -> None:
        token = _parse_bearer(auth_header)
        try:
            expected = config.get_node_token(node_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if token != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid node token")
        return None

    @app.post("/api/commands", dependencies=[Depends(get_admin_token)])
    def enqueue_command(payload: AdminCommandRequest):
        if not config.node_exists(payload.node_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown node")
        record = store.enqueue(payload.node_id, payload.action, payload.instance, payload.params)
        return {"command": record.to_api_dict()}

    @app.get("/api/commands", dependencies=[Depends(get_admin_token)])
    def list_commands(node_id: str | None = None):
        records = store.list_commands(node_id)
        return {"commands": [record.to_api_dict() for record in records]}

    @app.get("/api/nodes/{node_id}/commands", dependencies=[Depends(get_node_auth)])
    def fetch_commands(node_id: str):
        records = store.pending_for_node(node_id)
        return {"commands": [record.to_api_dict() for record in records]}

    @app.post("/api/nodes/{node_id}/commands/{command_id}/ack", dependencies=[Depends(get_node_auth)])
    def ack_command(node_id: str, command_id: str, payload: AckRequest):
        try:
            record = store.acknowledge(node_id, command_id, payload.success, payload.message)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return {"command": record.to_api_dict()}

    @app.post("/api/nodes/{node_id}/heartbeat", dependencies=[Depends(get_node_auth)])
    def receive_heartbeat(node_id: str, payload: HeartbeatRequest):
        record = hb_store.update(
            node_id=node_id,
            status=payload.status,
            instances=[instance.dict() for instance in payload.instances],
            message=payload.message,
            version=payload.version,
        )
        return {"heartbeat": record.to_api_dict()}

    @app.get("/api/heartbeats", dependencies=[Depends(get_admin_token)])
    def list_heartbeats():
        records = hb_store.list_statuses()
        return {"nodes": [record.to_api_dict() for record in records]}

    @app.post("/api/nodes/{node_id}/logs", dependencies=[Depends(get_node_auth)])
    def upload_logs(node_id: str, payload: LogUploadRequest):
        try:
            content = base64.b64decode(payload.content_b64)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base64 payload") from exc
        record = logs.create(
            node_id=node_id,
            instance=payload.instance,
            filename=payload.filename,
            content=content,
            command_id=payload.command_id,
        )
        return {"log": record.to_api_dict()}

    @app.get("/api/logs", dependencies=[Depends(get_admin_token)])
    def list_logs(node_id: str | None = None, command_id: str | None = None):
        records = logs.list_logs(node_id=node_id, command_id=command_id)
        return {"logs": [record.to_api_dict() for record in records]}

    @app.get("/api/logs/{log_id}", dependencies=[Depends(get_admin_token)])
    def download_log(log_id: str):
        record = logs.get(log_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
        return FileResponse(record.path, filename=record.filename, media_type="text/plain")

    return app


def _parse_bearer(header_value: str) -> str:
    if not header_value.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    return header_value.split(" ", 1)[1].strip()

"""
Host management routes.

GET  /hosts                  → list[Host]
POST /hosts                  → Host  (201)
GET  /hosts/{hostId}         → Host | 404
PATCH /hosts/{hostId}        → Host | 404
GET  /hosts/{hostId}/health  → Health  (proxies to agent /health, touches last_seen_at)
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ...agent_client import AgentClient, AgentError
from ...database import Database
from ..models import Health, Host, HostCreate, HostPatch

router = APIRouter()


def _row_to_host(row: dict) -> Host:
    return Host(
        id=row["id"],
        name=row["name"],
        agentUrl=row["agent_url"],
        agentApiKey=row["agent_api_key"],
        tags=row["tags"],
        notes=row["notes"],
        isEnabled=row["is_enabled"],
        createdAt=row["created_at"],
        lastSeenAt=row["last_seen_at"],
    )


async def _get_host_or_404(db: Database, host_id: str) -> dict:
    row = await db.get_host(host_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Host {host_id!r} not found")
    return row


@router.get("/hosts", response_model=list[Host])
async def list_hosts(request: Request) -> list[Host]:
    db: Database = request.app.state.db
    rows = await db.list_hosts()
    return [_row_to_host(r) for r in rows]


@router.post("/hosts", response_model=Host, status_code=201)
async def create_host(body: HostCreate, request: Request) -> JSONResponse:
    db: Database = request.app.state.db
    row = await db.create_host(
        name=body.name,
        agent_url=body.agentUrl,
        agent_api_key=body.agentApiKey,
        tags=body.tags,
        notes=body.notes,
    )
    return JSONResponse(status_code=201, content=_row_to_host(row).model_dump())


@router.get("/hosts/{hostId}", response_model=Host)
async def get_host(hostId: str, request: Request) -> Host:
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)
    return _row_to_host(row)


@router.patch("/hosts/{hostId}", response_model=Host)
async def patch_host(hostId: str, body: HostPatch, request: Request) -> Host:
    db: Database = request.app.state.db
    await _get_host_or_404(db, hostId)

    fields: dict = {}
    if body.name is not None:
        fields["name"] = body.name
    if body.agentUrl is not None:
        fields["agent_url"] = body.agentUrl
    if body.agentApiKey is not None:
        fields["agent_api_key"] = body.agentApiKey
    if body.tags is not None:
        fields["tags"] = body.tags
    if body.notes is not None:
        fields["notes"] = body.notes
    if body.isEnabled is not None:
        fields["is_enabled"] = body.isEnabled

    row = await db.update_host(hostId, fields)
    assert row is not None
    return _row_to_host(row)


@router.get("/hosts/{hostId}/health", response_model=Health)
async def get_host_health(hostId: str, request: Request) -> Health:
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    # Derive /agent/v1 base URL from the stored agentUrl
    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"

    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            data = await client.get_health()
        await db.touch_host(hostId)
        return Health(
            status=data.get("status", "unknown"),
            checkedAt=datetime.now(timezone.utc),
            notes=data.get("notes"),
        )
    except AgentError as exc:
        return Health(
            status="degraded",
            checkedAt=datetime.now(timezone.utc),
            notes=f"Agent returned {exc.status_code}: {exc.detail}",
        )
    except Exception as exc:
        return Health(
            status="down",
            checkedAt=datetime.now(timezone.utc),
            notes=f"Agent unreachable: {exc}",
        )


@router.get("/hosts/{hostId}/missions")
async def list_host_active_missions(hostId: str, request: Request) -> dict:
    """List the shared Active Missions folder on the agent host (root only)."""
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            items = await client.list_active_missions()
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    return {"items": items}


@router.get("/hosts/{hostId}/missions/{filename}")
async def download_host_mission(hostId: str, filename: str, request: Request):
    """Download a .miz file from the agent host's active_missions_dir."""
    from fastapi.responses import Response as FastAPIResponse
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            data = await client.download_active_mission(filename)
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    return FastAPIResponse(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/hosts/{hostId}/missions/upload")
async def upload_host_mission(hostId: str, request: Request) -> dict:
    """Upload a .miz to the agent host's active_missions_dir root."""
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    filename = ""
    cd = request.headers.get("Content-Disposition", "")
    for part in cd.split(";"):
        part = part.strip()
        if part.startswith("filename="):
            filename = part[len("filename="):].strip().strip('"')
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename in Content-Disposition header")
    if not filename.lower().endswith(".miz"):
        raise HTTPException(status_code=400, detail="Only .miz files are accepted")

    data = await request.body()
    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            return await client.upload_active_mission(filename, data)
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.delete("/hosts/{hostId}/missions/{filename}")
async def delete_host_mission(hostId: str, filename: str, request: Request) -> dict:
    """Move a .miz from active_missions_dir root to Backup_Missions/ (with backup)."""
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            return await client.delete_active_mission(filename)
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/hosts/{hostId}/reboot")
async def reboot_host(hostId: str, request: Request) -> dict:
    """Schedule a Windows reboot on the agent host (30-second grace period)."""
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            return await client.reboot_host()
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/hosts/{hostId}/update")
async def trigger_dcs_update(hostId: str, request: Request) -> dict:
    """Trigger a DCS update on the agent host. Fire-and-forget — poll /status for progress."""
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            return await client.trigger_dcs_update()
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/hosts/{hostId}/update/status")
async def get_update_status(hostId: str, request: Request) -> dict:
    """Return the current DCS update progress from the agent host."""
    db: Database = request.app.state.db
    row = await _get_host_or_404(db, hostId)

    agent_base = row["agent_url"].rstrip("/") + "/agent/v1"
    try:
        async with AgentClient(agent_base, row["agent_api_key"]) as client:
            return await client.get_update_status()
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

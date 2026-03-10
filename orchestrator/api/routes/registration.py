"""
Community host self-registration and invite code management.

POST /api/v1/register           — no auth, invite-code gated; used by installer
GET  /api/v1/invites            — admin only; list invite codes
POST /api/v1/invites            — admin only; create invite code
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ...database import Database
from ..auth import require_api_key
from ..models import (
    InviteCreate,
    InviteResponse,
    RegisterInstanceSpec,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter()

_ADMIN_DEP = [Depends(require_api_key)]


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_host(body: RegisterRequest, request: Request) -> JSONResponse:
    """
    Self-registration endpoint for community hosts.
    Requires a valid, unused invite code. Returns frp config and credentials.
    """
    db: Database = request.app.state.db
    config = request.app.state.config

    if not config.registration_enabled:
        raise HTTPException(status_code=403, detail="Host registration is currently disabled")

    if not config.frp_server_addr:
        raise HTTPException(status_code=503, detail="frp not configured on this orchestrator")

    # Validate invite
    invite = await db.get_invite_by_code(body.inviteCode)
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite code")
    if invite["used"]:
        raise HTTPException(status_code=400, detail="Invite code has already been used")
    if invite["expires_at"]:
        exp = datetime.fromisoformat(invite["expires_at"])
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(status_code=400, detail="Invite code has expired")

    # Assign frp port
    try:
        frp_port = await db.get_next_frp_port(
            config.frp_port_range_start, config.frp_port_range_end
        )
    except RuntimeError:
        raise HTTPException(status_code=503, detail="No frp ports available — contact admin")

    # Generate per-host agent API key
    agent_api_key = secrets.token_hex(32)
    agent_url = f"http://127.0.0.1:{frp_port}"

    # Create host
    host_name = body.hostName or invite["host_name"] or "Community Host"
    host_row = await db.create_host(
        name=host_name,
        agent_url=agent_url,
        agent_api_key=agent_api_key,
        tags=["community"],
        frp_port=frp_port,
    )

    # Mark invite used
    await db.consume_invite(body.inviteCode, host_row["id"])

    # Create any instances specified in the registration request
    instance_ids: list[str] = []
    for inst_spec in body.instances:
        inst_row = await db.create_instance(
            host_id=host_row["id"],
            service_name=inst_spec.serviceName,
            name=inst_spec.name,
            tags=["community"],
        )
        instance_ids.append(inst_row["id"])

    public_url = config.public_url or f"http://{config.frp_server_addr}:{config.port}"

    return JSONResponse(
        status_code=201,
        content=RegisterResponse(
            hostId=host_row["id"],
            hostName=host_name,
            agentApiKey=agent_api_key,
            orchestratorUrl=public_url,
            frpServerAddr=config.frp_server_addr,
            frpServerPort=config.frp_server_port,
            frpToken=config.frp_token,
            frpRemotePort=frp_port,
            instanceIds=instance_ids,
        ).model_dump(),
    )


@router.get("/invites", response_model=list[InviteResponse], dependencies=_ADMIN_DEP)
async def list_invites(request: Request) -> list[InviteResponse]:
    db: Database = request.app.state.db
    rows = await db.list_invites()
    return [InviteResponse(**r) for r in rows]


@router.post("/invites", response_model=InviteResponse, status_code=201, dependencies=_ADMIN_DEP)
async def create_invite(body: InviteCreate, request: Request) -> InviteResponse:
    db: Database = request.app.state.db
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=body.expiresInHours)
    ).isoformat()
    row = await db.create_invite(host_name=body.hostName, expires_at=expires_at)
    return InviteResponse(**row)

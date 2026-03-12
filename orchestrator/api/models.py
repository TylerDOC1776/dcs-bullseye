"""
Pydantic request/response models for orchestrator endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------


class HostCreate(BaseModel):
    name: str
    agentUrl: str
    agentApiKey: str = ""
    tags: list[str] = []
    notes: str | None = None


class HostPatch(BaseModel):
    name: str | None = None
    agentUrl: str | None = None
    agentApiKey: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    isEnabled: bool | None = None


class Host(BaseModel):
    id: str
    name: str
    agentUrl: str
    agentApiKey: str
    tags: list[str]
    notes: str | None
    isEnabled: bool
    createdAt: str
    lastSeenAt: str | None


# ---------------------------------------------------------------------------
# Instances
# ---------------------------------------------------------------------------


class InstanceCreate(BaseModel):
    hostId: str
    serviceName: str
    name: str
    tags: list[str] = []


class InstanceRef(BaseModel):
    id: str
    hostId: str
    serviceName: str
    name: str
    tags: list[str]
    createdAt: str


class InstanceStatus(str):
    pass


class InstanceRuntime(BaseModel):
    status: str  # running | stopped | starting | stopping | error | unknown
    observedAt: datetime
    pid: int | None = None
    startedAt: datetime | None = None
    uptimeSeconds: float | None = None
    missionStartedAt: datetime | None = None
    missionName: str | None = None
    map: str | None = None
    playerCount: int | None = None
    players: list[str] | None = None
    missionTimeSeconds: int | None = None
    lastExitCode: int | None = None
    lastError: str | None = None


class InstanceSummary(BaseModel):
    id: str
    hostId: str
    serviceName: str
    name: str
    tags: list[str]
    createdAt: str
    runtime: InstanceRuntime | None = None


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class JobAccepted(BaseModel):
    jobId: str
    status: str


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    instanceId: str | None
    hostId: str | None
    agentJobId: str | None
    createdAt: datetime
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Registration / Invite codes
# ---------------------------------------------------------------------------


class InviteCreate(BaseModel):
    hostName: str = ""
    expiresInHours: int = Field(default=24, ge=1, le=168)  # 1h minimum, 7d maximum


class InviteResponse(BaseModel):
    id: str
    code: str
    host_name: str
    used: bool
    used_by: str | None = None
    used_at: str | None = None
    created_at: str
    expires_at: str | None = None


class RegisterInstanceSpec(BaseModel):
    serviceName: str
    name: str


class RegisterRequest(BaseModel):
    inviteCode: str
    hostName: str = ""
    instances: list[RegisterInstanceSpec] = []


class RegisterResponse(BaseModel):
    hostId: str
    hostName: str
    agentApiKey: str
    orchestratorUrl: str
    frpServerAddr: str
    frpServerPort: int
    frpToken: str
    frpRemotePort: int
    instanceIds: list[str] = []


# ---------------------------------------------------------------------------
# Health / Problem
# ---------------------------------------------------------------------------


class Health(BaseModel):
    status: str  # ok | degraded | down
    checkedAt: datetime
    notes: str | None = None


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str | None = None

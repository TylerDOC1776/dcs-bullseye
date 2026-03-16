"""
Pydantic response models matching the OpenAPI schemas for Agent endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class InstanceStatus(str, Enum):
    running = "running"
    stopped = "stopped"
    starting = "starting"
    stopping = "stopping"
    degraded = "degraded"
    error = "error"
    unknown = "unknown"


_NSSM_STATUS_MAP: dict[str, InstanceStatus] = {
    "SERVICE_RUNNING": InstanceStatus.running,
    "SERVICE_STOPPED": InstanceStatus.stopped,
    "SERVICE_START_PENDING": InstanceStatus.starting,
    "SERVICE_STOP_PENDING": InstanceStatus.stopping,
    "SERVICE_PAUSED": InstanceStatus.stopped,
    "SERVICE_DEGRADED": InstanceStatus.degraded,
}


def nssm_to_instance_status(raw: str) -> InstanceStatus:
    """Map a raw NSSM status string to a typed InstanceStatus."""
    if raw in _NSSM_STATUS_MAP:
        return _NSSM_STATUS_MAP[raw]
    # NssmError surfaces as an error string
    if "ERROR" in raw.upper() or raw.lower().startswith("nssm"):
        return InstanceStatus.error
    return InstanceStatus.unknown


class Health(BaseModel):
    status: str  # ok | degraded | down
    checkedAt: datetime
    notes: str | None = None


class AgentCapabilities(BaseModel):
    os: str
    osVersion: str
    hostname: str
    pythonVersion: str
    supportedActions: list[str]
    notes: str | None = None


class InstanceSummary(BaseModel):
    instanceId: str
    name: str
    serviceName: str
    autoStart: bool
    ports: dict[str, Any]
    status: InstanceStatus


class InstanceRuntime(BaseModel):
    status: InstanceStatus
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


class JobAccepted(BaseModel):
    jobId: str
    status: str


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    instanceId: str | None
    createdAt: datetime
    startedAt: datetime | None = None
    finishedAt: datetime | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str | None = None

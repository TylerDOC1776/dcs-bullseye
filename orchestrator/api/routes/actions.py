"""
POST /api/v1/instances/{instanceId}/actions/{action}

Supported: start | stop | restart | logs_bundle | mission_load
Unsupported (not yet implemented): update → 400

mission_load requires a JSON body: {"mission": "filename.miz"}

Creates an orchestrator Job immediately, fires a background task that:
  1. Calls the agent to trigger the action (getting agentJobId)
  2. Polls the agent job until terminal
  3. Copies final status/result/error to the orchestrator job
  4. Publishes job.running / job.succeeded / job.failed events to the bus

Returns 202 JobAccepted immediately.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

import json

from ...agent_client import AgentClient, AgentError
from ...database import Database
from ...events import Event, EventBus
from ...jobs import Job, JobStore
from ..models import JobAccepted

router = APIRouter()

_SUPPORTED_ACTIONS = {"start", "stop", "restart", "logs_bundle", "mission_load", "reset_persist", "set_password"}
_UNSUPPORTED_ACTIONS = {"update"}
_POLL_INTERVAL = 2.0
_TIMEOUT_SECONDS = 300


def _job_event(event_type: str, job: Job) -> Event:
    return Event(
        type=event_type,
        instance_id=job.instance_id,
        host_id=job.host_id,
        data={
            "jobId": job.id,
            "action": job.type,
            "instanceId": job.instance_id,
            "error": job.error,
            "result": job.result,
        },
    )


async def _run_action(
    job: Job,
    store: JobStore,
    bus: EventBus,
    db: Database,
    host_row: dict,
    service_name: str,
    action: str,
    params: dict | None = None,
) -> None:
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    store.update(job)
    bus.publish(_job_event("job.running", job))

    agent_base = host_row["agent_url"].rstrip("/") + "/agent/v1"
    deadline = asyncio.get_event_loop().time() + _TIMEOUT_SECONDS

    async def _audit(status: str, detail: dict | None = None) -> None:
        await db.write_audit_log(
            action=action,
            status=status,
            actor=job.actor,
            instance_id=job.instance_id,
            host_id=job.host_id,
            job_id=job.id,
            detail=json.dumps(detail) if detail else None,
        )

    try:
        async with AgentClient(agent_base, host_row["agent_api_key"]) as client:
            try:
                accepted = await client.trigger_action(service_name, action, body=params)
            except AgentError as exc:
                job.status = "failed"
                job.error = {"message": f"Agent rejected action: {exc.detail}"}
                job.finished_at = datetime.now(timezone.utc)
                store.update(job)
                bus.publish(_job_event("job.failed", job))
                await _audit("failed", job.error)
                return

            agent_job_id: str = accepted.get("jobId", "")
            job.agent_job_id = agent_job_id
            store.update(job)

            terminal = {"succeeded", "failed"}
            while True:
                if asyncio.get_event_loop().time() > deadline:
                    job.status = "failed"
                    job.error = {"message": "timeout waiting for agent job"}
                    job.finished_at = datetime.now(timezone.utc)
                    store.update(job)
                    bus.publish(_job_event("job.failed", job))
                    await _audit("failed", job.error)
                    return

                await asyncio.sleep(_POLL_INTERVAL)

                try:
                    agent_job = await client.get_job(agent_job_id)
                except AgentError:
                    continue  # transient — keep polling

                agent_status = agent_job.get("status", "")
                if agent_status in terminal:
                    job.status = agent_status
                    job.result = agent_job.get("result")
                    job.error = agent_job.get("error")
                    job.finished_at = datetime.now(timezone.utc)
                    store.update(job)
                    event_type = "job.succeeded" if agent_status == "succeeded" else "job.failed"
                    bus.publish(_job_event(event_type, job))
                    await _audit(agent_status, job.error or job.result)
                    return

    except Exception as exc:
        job.status = "failed"
        job.error = {"message": str(exc)}
        job.finished_at = datetime.now(timezone.utc)
        store.update(job)
        bus.publish(_job_event("job.failed", job))
        await _audit("failed", job.error)


@router.post(
    "/instances/{instanceId}/actions/{action}",
    response_model=JobAccepted,
    status_code=202,
)
async def trigger_action(
    instanceId: str,
    action: str,
    request: Request,
) -> JSONResponse:
    if action in _UNSUPPORTED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Action {action!r} is not yet implemented",
        )
    if action not in _SUPPORTED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action {action!r}. Supported: {sorted(_SUPPORTED_ACTIONS)}",
        )

    db: Database = request.app.state.db
    store: JobStore = request.app.state.job_store
    bus: EventBus = request.app.state.event_bus

    # Parse optional body; required for mission_load
    params: dict = {}
    try:
        body = await request.json()
        if isinstance(body, dict):
            params = body
    except Exception:
        pass

    if action == "mission_load" and not params.get("mission"):
        raise HTTPException(
            status_code=400,
            detail='mission_load requires a JSON body: {"mission": "filename.miz"}',
        )

    if action == "set_password" and "password" not in params:
        raise HTTPException(
            status_code=400,
            detail='set_password requires a JSON body: {"password": "..."}',
        )

    actor = request.headers.get("X-Discord-User-Id") or None

    inst_row = await db.get_instance(instanceId)
    if inst_row is None:
        raise HTTPException(status_code=404, detail=f"Instance {instanceId!r} not found")

    host_row = await db.get_host(inst_row["host_id"])
    if host_row is None:
        raise HTTPException(status_code=404, detail=f"Host {inst_row['host_id']!r} not found")

    job = store.create(
        type=action,
        instance_id=instanceId,
        host_id=inst_row["host_id"],
        actor=actor,
    )
    bus.publish(_job_event("job.queued", job))
    await db.write_audit_log(
        action=action,
        status="queued",
        actor=actor,
        instance_id=instanceId,
        host_id=inst_row["host_id"],
        job_id=job.id,
    )

    asyncio.create_task(
        _run_action(job, store, bus, db, host_row, inst_row["service_name"], action, params)
    )

    return JSONResponse(
        status_code=202,
        content=JobAccepted(jobId=job.id, status=job.status).model_dump(),
    )

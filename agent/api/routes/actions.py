"""
POST /agent/v1/instances/{instanceId}/actions/{action}

Supported: start | stop | restart | logs_bundle | mission_load
Unsupported (not yet implemented): update → 400

Creates a Job immediately, fires a background task, returns 202 JobAccepted.
NSSM calls are wrapped in run_in_executor so they don't block the event loop.

mission_load requires a JSON body: {"mission": "filename.miz"}
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ...config import InstanceConfig
from ...controller import DcsController, _read_hook_status, redact_line
from ...jobs import Job, JobStore
from ..models import JobAccepted
from .instances import find_instance


async def _minimize_after_load(inst: InstanceConfig, ctrl: DcsController) -> None:
    """Background task: wait for DCS mission to finish loading, then minimize windows.

    Two-phase: first wait for mission_loaded to go False (new load starting),
    then wait for it to go True (load complete). This avoids acting on the stale
    True value left in the status file from the previous server run.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 600  # up to 10 min total
    saw_loading = False
    while loop.time() < deadline:
        await asyncio.sleep(10)
        hook = _read_hook_status(inst.log_path)
        loaded = hook.get("mission_loaded")
        if not loaded:
            saw_loading = True  # mission is in-progress (or DCS hasn't started yet)
        elif saw_loading:
            # Transitioned False → True: mission freshly loaded
            try:
                ctrl.minimize_windows()
            except Exception:
                pass
            return

router = APIRouter()

_SUPPORTED_ACTIONS = {"start", "stop", "restart", "logs_bundle", "mission_load", "minimize_window", "reset_persist", "set_password"}
_UNSUPPORTED_ACTIONS = {"update"}


async def _execute_job(
    job: Job,
    store: JobStore,
    ctrl: DcsController,
    inst: InstanceConfig,
    action: str,
    params: dict | None = None,
) -> None:
    loop = asyncio.get_running_loop()
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    store.update(job)

    try:
        if action == "start":
            await loop.run_in_executor(None, ctrl.start, inst)
            asyncio.create_task(_minimize_after_load(inst, ctrl))
            job.result = {"message": f"Service {inst.service_name} started"}
        elif action == "stop":
            await loop.run_in_executor(None, ctrl.stop, inst)
            job.result = {"message": f"Service {inst.service_name} stopped"}
        elif action == "restart":
            await loop.run_in_executor(None, ctrl.restart, inst)
            asyncio.create_task(_minimize_after_load(inst, ctrl))
            job.result = {"message": f"Service {inst.service_name} restarted"}
        elif action == "logs_bundle":
            lines = await loop.run_in_executor(None, ctrl.tail_logs, inst, 200)
            errors = await loop.run_in_executor(None, ctrl.parse_errors, inst, 5000)
            lines = [redact_line(l) for l in lines]
            scripting = [redact_line(l) for l in errors["scripting_errors"]]
            dcs_errs = [redact_line(l) for l in errors["dcs_errors"]]
            job.result = {"lines": lines, "scripting_errors": scripting, "dcs_errors": dcs_errs}
        elif action == "mission_load":
            mission_file: str = (params or {}).get("mission", "")
            mission_path = await loop.run_in_executor(
                None, ctrl.mission_load, inst, mission_file
            )
            job.result = {"message": f"Mission loaded and server restarted", "mission": mission_path}
        elif action == "minimize_window":
            await loop.run_in_executor(None, ctrl.minimize_windows)
            job.result = {"message": "DCS windows minimized"}
        elif action == "reset_persist":
            result = await loop.run_in_executor(None, ctrl.reset_persist, inst)
            job.result = result
        elif action == "set_password":
            password: str = (params or {}).get("password", "")
            await loop.run_in_executor(None, ctrl.set_password, inst, password)
            job.result = {"message": "Password updated and server restarted"}
        job.status = "succeeded"
    except Exception as exc:
        job.status = "failed"
        job.error = {"message": str(exc)}
    finally:
        job.finished_at = datetime.now(timezone.utc)
        store.update(job)


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

    config = request.app.state.config
    ctrl: DcsController = request.app.state.controller
    store: JobStore = request.app.state.job_store

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

    inst = find_instance(config, instanceId)
    job = store.create(type=action, instance_id=inst.service_name)

    asyncio.create_task(_execute_job(job, store, ctrl, inst, action, params))

    return JSONResponse(
        status_code=202,
        content=JobAccepted(jobId=job.id, status=job.status).model_dump(),
    )


@router.post("/host/reboot")
async def reboot_host(request: Request) -> dict:
    """Schedule a Windows reboot with a 30-second grace period. Fire-and-forget — returns immediately."""
    ctrl: DcsController = request.app.state.controller
    return ctrl.reboot_host()


@router.post("/host/update")
async def trigger_dcs_update(request: Request) -> dict:
    """Trigger the DCS-UpdateDCS Task Scheduler task to update DCS non-interactively.
    Fire-and-forget — returns immediately. Poll /host/update/status for progress."""
    ctrl: DcsController = request.app.state.controller
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, ctrl.trigger_dcs_update)
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/host/update/status")
async def get_update_status(request: Request) -> dict:
    """Return the current DCS update progress from the status file written by the update script."""
    ctrl: DcsController = request.app.state.controller
    return ctrl.get_update_status()

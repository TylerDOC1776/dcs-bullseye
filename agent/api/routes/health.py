"""
GET /health — unauthenticated heartbeat endpoint.

Probes nssm via `nssm version` to determine agent health. Returns ok or degraded.
No auth required so orchestrators and load balancers can poll without credentials.
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from ..models import Health

router = APIRouter()


@router.get("/health", response_model=Health)
async def get_health(request: Request) -> Health:
    config = request.app.state.config
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [config.nssm_path, "version"],
                capture_output=True,
                text=True,
                timeout=5,
            ),
        )
        if result.returncode == 0:
            return Health(status="ok", checkedAt=datetime.now(timezone.utc))
        return Health(
            status="degraded",
            checkedAt=datetime.now(timezone.utc),
            notes=f"nssm version exited {result.returncode}",
        )
    except Exception as exc:
        return Health(
            status="degraded",
            checkedAt=datetime.now(timezone.utc),
            notes=f"nssm unreachable: {exc}",
        )

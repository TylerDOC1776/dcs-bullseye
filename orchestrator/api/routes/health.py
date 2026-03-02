"""
GET /health — unauthenticated heartbeat endpoint.

Probes the SQLite database with SELECT 1 to determine orchestrator health.
No auth required so load balancers and monitoring can poll without credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from ..models import Health

router = APIRouter()


@router.get("/health", response_model=Health)
async def get_health(request: Request) -> Health:
    db = request.app.state.db
    ok = await db.probe()
    if ok:
        return Health(status="ok", checkedAt=datetime.now(timezone.utc))
    return Health(
        status="degraded",
        checkedAt=datetime.now(timezone.utc),
        notes="Database probe failed",
    )

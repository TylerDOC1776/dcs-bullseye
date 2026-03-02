"""
GET /api/v1/events/stream  — Server-Sent Events stream (live push)
GET /api/v1/events/recent  — Recent events (polling fallback)

SSE format per https://html.spec.whatwg.org/multipage/server-sent-events.html:

    id: <event_id>
    event: <event_type>
    data: <json_payload>
    (blank line)

Filter via query params:
  types      — comma-separated event type list (e.g. "job.failed,instance.status_changed")
  instanceId — limit to a specific orchestrator instance id
  hostId     — limit to a specific host id
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from ...events import EventBus

router = APIRouter()

_KEEPALIVE_SECS = 15.0


async def _sse_generator(
    bus: EventBus,
    types: set[str] | None,
    instance_id: str | None,
    host_id: str | None,
    request: Request,
) -> AsyncGenerator[str, None]:
    q = bus.subscribe()
    try:
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_SECS)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            if event is None:
                break
            if types and event.type not in types:
                continue
            if instance_id and event.instance_id != instance_id:
                continue
            if host_id and event.host_id != host_id:
                continue
            yield event.to_sse()
    finally:
        bus.unsubscribe(q)


@router.get("/events/stream")
async def sse_stream(
    request: Request,
    types: str | None = Query(None, description="Comma-separated event types to include"),
    instanceId: str | None = Query(None),
    hostId: str | None = Query(None),
) -> StreamingResponse:
    bus: EventBus = request.app.state.event_bus
    type_set = {t.strip() for t in types.split(",")} if types else None
    return StreamingResponse(
        _sse_generator(bus, type_set, instanceId, hostId, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx proxy buffering
        },
    )


@router.get("/events/recent")
async def recent_events(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    since: str | None = Query(None, description="ISO 8601 — return events at or after this time"),
    types: str | None = Query(None),
    instanceId: str | None = Query(None),
    hostId: str | None = Query(None),
) -> dict:
    bus: EventBus = request.app.state.event_bus
    type_set = {t.strip() for t in types.split(",")} if types else None
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            pass
    events = bus.recent(
        types=type_set,
        instance_id=instanceId,
        host_id=hostId,
        since=since_dt,
        limit=limit,
    )
    return {"items": [e.to_dict() for e in events]}

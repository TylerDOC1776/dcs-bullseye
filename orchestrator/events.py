"""
In-process event bus for the DCS orchestrator.

Events are published by action tasks and the status poller, then
pushed to all active SSE/WebSocket subscribers via asyncio queues.
A fixed-size history ring allows polling clients to catch up.

Event types:
  job.queued          — job created
  job.running         — job started executing
  job.succeeded       — job completed successfully
  job.failed          — job completed with error
  instance.status_changed — periodic poller detected a status change
"""

from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_HISTORY_SIZE = 200


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: secrets.token_hex(8))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    instance_id: str | None = None
    host_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "instanceId": self.instance_id,
            "hostId": self.host_id,
            "data": self.data,
        }

    def to_sse(self) -> str:
        payload = json.dumps(self.to_dict())
        return f"id: {self.id}\nevent: {self.type}\ndata: {payload}\n\n"


class EventBus:
    """
    Synchronous publish (no awaits), async subscribe via asyncio.Queue.

    All operations run in the same event loop — no locking needed.
    """

    def __init__(self, history_size: int = _HISTORY_SIZE) -> None:
        self._subscribers: list[asyncio.Queue[Event | None]] = []
        self._history: list[Event] = []
        self._history_size = history_size

    def publish(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._history_size:
            del self._history[: -self._history_size]
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow consumer — drop rather than block

    def subscribe(self, maxsize: int = 100) -> asyncio.Queue[Event | None]:
        q: asyncio.Queue[Event | None] = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def recent(
        self,
        *,
        types: set[str] | None = None,
        instance_id: str | None = None,
        host_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]:
        events: list[Event] = self._history
        if types:
            events = [e for e in events if e.type in types]
        if instance_id:
            events = [e for e in events if e.instance_id == instance_id]
        if host_id:
            events = [e for e in events if e.host_id == host_id]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events[-limit:]

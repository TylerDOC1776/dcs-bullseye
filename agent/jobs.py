"""
In-memory job store for async agent actions.

Jobs are created immediately (status=queued) and updated by background tasks.
The store is not persisted — agent restart clears all jobs.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class Job:
    id: str  # "job_<12-hex>"
    type: str  # action name e.g. "start"
    status: str  # queued | running | succeeded | failed
    instance_id: str | None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, type: str, instance_id: str | None) -> Job:
        job_id = "job_" + secrets.token_hex(6)
        job = Job(
            id=job_id,
            type=type,
            status="queued",
            instance_id=instance_id,
            created_at=datetime.now(timezone.utc),
        )
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        self._jobs[job.id] = job

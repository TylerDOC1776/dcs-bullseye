"""
GET /api/v1/jobs           — list all jobs (optional ?status= filter)
GET /api/v1/jobs/{jobId}   — get a single job by id
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...jobs import Job
from ..models import JobResponse

router = APIRouter()


def _job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        instanceId=job.instance_id,
        hostId=job.host_id,
        agentJobId=job.agent_job_id,
        createdAt=job.created_at,
        startedAt=job.started_at,
        finishedAt=job.finished_at,
        result=job.result,
        error=job.error,
    )


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(request: Request, status: str | None = None) -> list[JobResponse]:
    store = request.app.state.job_store
    jobs = store.list(status=status)
    return [_job_to_response(j) for j in jobs]


@router.get("/jobs/{jobId}", response_model=JobResponse)
async def get_job(jobId: str, request: Request) -> JobResponse:
    store = request.app.state.job_store
    job = store.get(jobId)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {jobId!r} not found")
    return _job_to_response(job)

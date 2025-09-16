"""
Job management API endpoints for tracking processing status.

Provides GET /api/jobs/status/{job_id} endpoint for real-time job progress
monitoring with detailed status information and download URLs.
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.models import Job, JobStatus

logger = structlog.get_logger("urbaniq.api.jobs")

router = APIRouter(tags=["jobs"], prefix="/jobs")


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")
    bezirk: str | None = Field(None, description="Extracted Berlin district")
    datasets: list[str] | None = Field(None, description="Requested datasets")
    download_url: str | None = Field(None, description="Package download URL when completed")
    error_message: str | None = Field(None, description="Error details when failed")


class ErrorResponse(BaseModel):
    """Structured error response model."""

    error: dict[str, Any] = Field(..., description="Error details")

    @classmethod
    def create(
        cls, code: str, message: str, details: dict[str, Any] | None = None
    ) -> "ErrorResponse":
        """Create standardized error response."""
        return cls(error={"code": code, "message": message, "details": details or {}})


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Retrieve current status and progress for a geodata processing job",
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"description": "Job not found", "model": ErrorResponse},
        500: {"description": "Database error", "model": ErrorResponse},
    },
)
async def get_job_status(request: Request, job_id: str, session: SessionDep) -> JobStatusResponse:
    """
    Get current status and progress for a geodata processing job.

    Returns detailed job information including progress percentage,
    processing status, and download URL when completed.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    request_logger = logger.bind(correlation_id=correlation_id, job_id=job_id)

    request_logger.info("Job status request received")

    try:
        # Query job from database
        job = session.get(Job, job_id)

        if not job:
            request_logger.warning("Job not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.create(
                    code="JOB_NOT_FOUND",
                    message="Verarbeitungsauftrag nicht gefunden",
                    details={"job_id": job_id},
                ).model_dump(),
            )

        # Parse datasets if available
        datasets = None
        if job.datasets:
            try:
                import json

                datasets = json.loads(job.datasets)
            except (json.JSONDecodeError, TypeError):
                request_logger.warning("Failed to parse job datasets", datasets=job.datasets)

        # Generate download URL if job is completed
        download_url = None
        if job.status == JobStatus.COMPLETED and job.result_package_id:
            download_url = f"/api/packages/{job.result_package_id}"

        response = JobStatusResponse(
            job_id=job.id,
            status=job.status.value,
            progress=job.progress,
            created_at=job.created_at,
            completed_at=job.completed_at,
            bezirk=job.bezirk,
            datasets=datasets,
            download_url=download_url,
            error_message=job.error_message,
        )

        request_logger.info(
            "Job status retrieved",
            status=job.status.value,
            progress=job.progress,
            bezirk=job.bezirk,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Failed to retrieve job status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                code="DATABASE_ERROR",
                message="Fehler beim Abrufen des Auftragsstatus",
                details={"error": str(e)},
            ).model_dump(),
        ) from e


@router.get(
    "/",
    response_model=list[JobStatusResponse],
    summary="List recent jobs",
    description="Retrieve list of recent geodata processing jobs (limited to 50)",
    responses={
        200: {"description": "Job list retrieved successfully"},
        500: {"description": "Database error", "model": ErrorResponse},
    },
)
async def list_jobs(
    request: Request, session: SessionDep, limit: int = 50
) -> list[JobStatusResponse]:
    """
    List recent geodata processing jobs.

    Returns a list of recent jobs ordered by creation date (newest first),
    limited to the specified number of results.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    request_logger = logger.bind(correlation_id=correlation_id)

    request_logger.info("Job list request received", limit=limit)

    try:
        from sqlmodel import desc, select

        # Query recent jobs ordered by creation date
        statement = select(Job).order_by(desc(Job.created_at)).limit(min(limit, 100))
        jobs = session.exec(statement).all()

        job_responses = []
        for job in jobs:
            # Parse datasets if available
            datasets = None
            if job.datasets:
                try:
                    import json

                    datasets = json.loads(job.datasets)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Generate download URL if completed
            download_url = None
            if job.status == JobStatus.COMPLETED and job.result_package_id:
                download_url = f"/api/packages/{job.result_package_id}"

            job_responses.append(
                JobStatusResponse(
                    job_id=job.id,
                    status=job.status.value,
                    progress=job.progress,
                    created_at=job.created_at,
                    completed_at=job.completed_at,
                    bezirk=job.bezirk,
                    datasets=datasets,
                    download_url=download_url,
                    error_message=job.error_message,
                )
            )

        request_logger.info("Job list retrieved", job_count=len(job_responses))
        return job_responses

    except Exception as e:
        request_logger.error("Failed to retrieve job list", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                code="DATABASE_ERROR",
                message="Fehler beim Abrufen der Auftragsliste",
                details={"error": str(e)},
            ).model_dump(),
        ) from e

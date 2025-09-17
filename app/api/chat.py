"""
Chat interface API endpoints for natural language geodata requests.

Provides POST /api/chat/message endpoint that accepts natural language input,
parses it via NLP service, creates background processing jobs, and returns job IDs.
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.api.deps import SessionDep, SettingsDep
from app.models import Job, JobStatus

from .chat_background import process_geodata_request_sync as process_geodata_request

logger = structlog.get_logger("urbaniq.api.chat")

router = APIRouter(tags=["chat"], prefix="/chat")


class ChatMessage(BaseModel):
    """Request model for natural language geodata requests."""

    text: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Natural language geodata request in German",
        examples=["Pankow Gebäude und ÖPNV-Haltestellen für Mobilitätsanalyse"],
    )
    user_id: str | None = Field(
        None, max_length=100, description="Optional user identifier for tracking"
    )

    @field_validator("text")
    @classmethod
    def validate_text_content(cls, v: str) -> str:
        """Validate text contains meaningful content."""
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for chat message submission."""

    job_id: str = Field(..., description="Unique job identifier for status tracking")
    status: str = Field(..., description="Initial job status")
    message: str = Field(..., description="Human-readable status message")


class ErrorResponse(BaseModel):
    """Structured error response model."""

    error: dict[str, Any] = Field(..., description="Error details")

    @classmethod
    def create(
        cls, code: str, message: str, details: dict[str, Any] | None = None
    ) -> "ErrorResponse":
        """Create standardized error response."""
        return cls(error={"code": code, "message": message, "details": details or {}})


@router.post(
    "/message",
    response_model=ChatResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit geodata request",
    description="Process natural language geodata requests for Berlin districts",
    responses={
        202: {"description": "Request accepted, job created"},
        400: {"description": "Invalid request or low confidence parsing", "model": ErrorResponse},
        500: {"description": "Service unavailable or processing error", "model": ErrorResponse},
    },
)
async def submit_chat_message(
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    _settings: SettingsDep,
    text: str = Form(..., min_length=5, max_length=500, description="Natural language geodata request"),
) -> ChatResponse:
    """
    Submit natural language geodata request for processing.

    Creates a background job that processes the request through the complete
    service chain: NLP → Data → Processing → Metadata services.
    """
    # Validate text input
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text cannot be empty or whitespace only"
        )

    text = text.strip()

    correlation_id = getattr(request.state, "correlation_id", "unknown")
    request_logger = logger.bind(
        correlation_id=correlation_id,
        user_text=text[:100] + "..." if len(text) > 100 else text,
    )

    request_logger.info("Received chat message request")

    try:
        # Create job record
        job = Job(request_text=text, status=JobStatus.PENDING, progress=0)

        session.add(job)
        session.commit()
        session.refresh(job)

        request_logger.info("Job created", job_id=job.id)

        # Add background task for processing
        # Note: Passing session factory instead of session to avoid connection issues
        background_tasks.add_task(
            process_geodata_request,
            job.id,
            text,
            lambda: session.__class__(bind=session.bind),  # Session factory
        )

        return ChatResponse(
            job_id=job.id,
            status="processing",
            message=f"Geodaten-Anfrage wird verarbeitet. Job-ID: {job.id}",
        )

    except Exception as e:
        request_logger.error("Failed to create job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                code="JOB_CREATION_FAILED",
                message="Fehler beim Erstellen des Verarbeitungsauftrags",
                details={"error": str(e)},
            ).model_dump(),
        ) from e

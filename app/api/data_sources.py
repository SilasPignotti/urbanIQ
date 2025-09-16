"""
Data source registry API endpoints for available datasets.

Provides endpoints for managing and querying available geodata sources.
This is a basic structure for future implementation.
"""

from typing import Any

import structlog
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.api.deps import SessionDep

logger = structlog.get_logger("urbaniq.api.data_sources")

router = APIRouter(tags=["data-sources"], prefix="/data-sources")


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
    "/",
    summary="List data sources",
    description="List available geodata sources and their status",
    responses={501: {"description": "Not implemented", "model": ErrorResponse}},
)
async def list_data_sources(request: Request, _session: SessionDep) -> None:
    """
    List available geodata sources.

    This endpoint will provide information about available Berlin Geoportal
    and OpenStreetMap data sources with health status and metadata.
    Currently returns a placeholder response.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    request_logger = logger.bind(correlation_id=correlation_id)

    request_logger.info("Data sources list request received")

    # TODO: Implement data source registry functionality
    # - Query DataSource model from database
    # - Return source metadata and health status
    # - Support filtering by category/type

    from fastapi import HTTPException

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=ErrorResponse.create(
            code="NOT_IMPLEMENTED",
            message="Data source registry wird in einer zukünftigen Version implementiert",
            details={"feature": "data source management"},
        ).model_dump(),
    )

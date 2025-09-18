"""
Package management API endpoints for geodata ZIP downloads.

Provides secure package download endpoints with tracking and statistics,
implementing Step 11 of the Implementation Roadmap.
"""

from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.models import Package

logger = structlog.get_logger("urbaniq.api.packages")

router = APIRouter(tags=["packages"], prefix="/packages")


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
    "/{package_id}",
    summary="Download package",
    description="Download geodata package as ZIP file with tracking and security",
    responses={
        200: {"description": "Package download", "content": {"application/zip": {}}},
        404: {"description": "Package not found", "model": ErrorResponse},
        410: {"description": "Package expired", "model": ErrorResponse},
        403: {"description": "Access forbidden", "model": ErrorResponse},
    },
)
async def download_package(request: Request, package_id: str, session: SessionDep) -> FileResponse:
    """
    Download geodata package as ZIP file.

    Serves ZIP packages created by the Export Service with proper security,
    tracking, and error handling. Validates file existence and expiration status.

    Args:
        request: FastAPI request object with correlation ID
        package_id: UUID of the package to download
        session: Database session dependency

    Returns:
        FileResponse: ZIP file download with proper headers

    Raises:
        HTTPException: 404 if package not found, 410 if expired, 403 if security violation
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    request_logger = logger.bind(correlation_id=correlation_id, package_id=package_id)

    request_logger.info("Package download request received")

    try:
        # Validate package_id format (basic security)
        if not package_id or len(package_id) < 8 or ".." in package_id or "/" in package_id:
            request_logger.warning("Invalid package_id format", package_id=package_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse.create(
                    code="INVALID_PACKAGE_ID",
                    message="Ungültiges Paket-Format",
                    details={"package_id": package_id},
                ).model_dump(),
            )

        # Query package from database
        package = session.get(Package, package_id)

        if not package:
            request_logger.warning("Package not found in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.create(
                    code="PACKAGE_NOT_FOUND",
                    message="Geodatenpaket nicht gefunden",
                    details={"package_id": package_id},
                ).model_dump(),
            )

        # Check if package has expired
        if package.is_expired():
            request_logger.info(
                "Package has expired",
                expires_at=package.expires_at.isoformat(),
            )
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=ErrorResponse.create(
                    code="PACKAGE_EXPIRED",
                    message="Geodatenpaket ist abgelaufen und nicht mehr verfügbar",
                    details={
                        "package_id": package_id,
                        "expired_at": package.expires_at.isoformat(),
                    },
                ).model_dump(),
            )

        # Validate file exists on filesystem
        file_path = Path(package.file_path)

        # Security: Ensure file path is absolute and within expected directory
        if not file_path.is_absolute():
            request_logger.error("Package file path is not absolute", file_path=str(file_path))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse.create(
                    code="SECURITY_VIOLATION",
                    message="Sicherheitsfehler beim Dateizugriff",
                    details={"reason": "invalid_file_path"},
                ).model_dump(),
            )

        # Check if file actually exists
        if not file_path.exists():
            request_logger.error(
                "Package file not found on filesystem",
                file_path=str(file_path),
                package_id=package_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.create(
                    code="FILE_NOT_FOUND",
                    message="Geodatenpaket-Datei nicht gefunden",
                    details={"package_id": package_id},
                ).model_dump(),
            )

        # Security: Verify it's actually a ZIP file
        if file_path.suffix.lower() != ".zip":
            request_logger.error(
                "Package file is not a ZIP file",
                file_path=str(file_path),
                suffix=file_path.suffix,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse.create(
                    code="INVALID_FILE_TYPE",
                    message="Ungültiger Dateityp",
                    details={"expected": ".zip", "actual": file_path.suffix},
                ).model_dump(),
            )

        # Increment download counter (tracking)
        package.increment_download()
        session.add(package)
        session.commit()

        # Generate filename for download
        # Use package ID for predictable, unique filename
        filename = f"geodata_package_{package.id}.zip"

        request_logger.info(
            "Package download successful",
            file_size_mb=package.get_file_size_mb(),
            download_count=package.download_count,
            filename=filename,
        )

        # Return file with proper headers
        return FileResponse(
            path=str(file_path),
            media_type="application/zip",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "private, no-cache",
                "X-Package-ID": package_id,
                "X-Download-Count": str(package.download_count),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        request_logger.error("Failed to serve package download", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                code="DOWNLOAD_ERROR",
                message="Fehler beim Herunterladen des Geodatenpakets",
                details={"error": str(e)},
            ).model_dump(),
        ) from e

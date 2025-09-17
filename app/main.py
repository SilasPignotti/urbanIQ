"""
FastAPI application factory and configuration.

Main application entry point with middleware setup, CORS configuration,
structured logging, and API router registration for the urbanIQ system.
"""

import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.data_sources import router as data_sources_router
from app.api.frontend import router as frontend_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.packages import router as packages_router
from app.config import settings
from app.database import create_db_and_tables


# Configure structured logging
def setup_logging() -> None:
    """Configure structured JSON logging with correlation IDs."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FUNC_NAME]
            ),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer()
            if settings.is_development
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=settings.log_level_int,
        handlers=[logging.StreamHandler()],
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan management.

    Handles startup and shutdown events for the FastAPI application,
    including database initialization and cleanup.
    """
    # Startup
    setup_logging()
    logger = structlog.get_logger(__name__)

    logger.info(
        "Starting urbanIQ application",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Ensure required directories exist
    settings.ensure_directories()

    # Initialize database
    create_db_and_tables()
    logger.info("Database initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down urbanIQ application")


def create_app() -> FastAPI:
    """
    FastAPI application factory.

    Creates and configures the FastAPI application with all middleware,
    routers, and configuration needed for the urbanIQ system.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="urbanIQ Berlin",
        description="Intelligent geodata aggregation system for Berlin urban planning",
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request correlation ID middleware
    @app.middleware("http")
    async def add_correlation_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add correlation ID to each request for tracing."""
        correlation_id = str(uuid.uuid4())

        # Add to request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Add to structlog context
        with structlog.contextvars.bound_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        ):
            logger = structlog.get_logger(__name__)
            logger.info("Request started")

            response: Response = await call_next(request)

            logger.info(
                "Request completed",
                status_code=response.status_code,
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Global exception handler with structured logging."""
        logger = structlog.get_logger(__name__)
        logger.error(
            "Unhandled exception occurred",
            exception=str(exc),
            exception_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

    # Mount static files
    static_dir = Path(__file__).parent / "frontend" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(packages_router, prefix="/api")
    app.include_router(data_sources_router, prefix="/api")

    # Include frontend router (no prefix for root paths)
    app.include_router(frontend_router)

    return app


# Application instance
app = create_app()

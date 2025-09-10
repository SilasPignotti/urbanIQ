"""
Database configuration and session management.

Provides SQLite session management with SQLModel, connection pooling,
and database initialization utilities for the urbanIQ application.
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.config import settings


def get_engine() -> Engine:
    """Create and configure SQLite engine."""
    connect_args = {"check_same_thread": False}

    # SQLite-specific configuration for development
    if settings.database_url.startswith("sqlite"):
        engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
            poolclass=StaticPool,
            echo=settings.debug,  # Log SQL queries in debug mode
        )
    else:
        # PostgreSQL or other databases for production
        engine = create_engine(
            settings.database_url,
            echo=settings.debug,
        )

    return engine


# Global engine instance
engine = get_engine()


def create_db_and_tables() -> None:
    """Create database and all tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields:
        Session: SQLModel database session

    Usage:
        @app.get("/endpoint")
        def endpoint(session: Session = Depends(get_session)):
            # Use session for database operations
            pass
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def check_database_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with Session(engine) as session:
            # Simple query to test connection
            session.execute(text("SELECT 1")).first()
            return True
    except Exception:
        return False

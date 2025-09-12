"""
FastAPI dependency injection setup.

Provides reusable dependencies for database sessions, configuration,
and future service integrations across the application.
"""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.config import Settings, settings
from app.database import get_session

# Type aliases for dependency injection
SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(lambda: settings)]


def get_current_settings() -> Settings:
    """
    Get current application settings.

    Returns:
        Settings: Current application settings instance
    """
    return settings

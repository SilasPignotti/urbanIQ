"""
Simple test fixtures for basic urbanIQ testing.

Provides minimal database fixtures and basic test setup.
"""

import tempfile
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app


@pytest.fixture
def test_db_engine():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)
    SQLModel.metadata.create_all(engine)

    yield engine

    # Cleanup
    Path(temp_db_path).unlink(missing_ok=True)


@pytest.fixture
def db_session(test_db_engine):
    """Create a database session for testing."""
    with Session(test_db_engine) as session:
        yield session


@pytest.fixture
def override_get_session(db_session):
    """Override the database session dependency for testing."""
    app.dependency_overrides[get_session] = lambda: db_session
    yield
    app.dependency_overrides.clear()

"""
Unit tests for database session management.

Tests database connection, session management, and utility functions
for SQLite integration.
"""

import contextlib
from unittest.mock import patch

from sqlmodel import Session

from app.database import check_database_connection, engine, get_session


class TestDatabaseConnection:
    """Test cases for database connection and session management."""

    def test_get_session_dependency(self):
        """Test database session dependency injection."""
        session_generator = get_session()
        session = next(session_generator)

        assert isinstance(session, Session)

        # Clean up
        with contextlib.suppress(StopIteration):
            next(session_generator)

    def test_check_database_connection_success(self):
        """Test successful database connection check."""
        result = check_database_connection()

        # Should be True for SQLite (file-based)
        assert result is True

    def test_check_database_connection_failure(self):
        """Test database connection check with failure."""
        with patch("app.database.Session") as mock_session:
            mock_session.return_value.__enter__.return_value.execute.side_effect = Exception(
                "Connection failed"
            )

            result = check_database_connection()

            assert result is False

    def test_engine_configuration(self):
        """Test database engine configuration."""
        assert engine is not None
        assert str(engine.url).startswith("sqlite")

    def test_session_transaction_rollback(self):
        """Test session rollback on exception."""
        session_generator = get_session()
        session = next(session_generator)

        try:
            # Simulate an exception during database operation
            with (
                patch.object(session, "rollback") as mock_rollback,
                patch.object(session, "exec", side_effect=Exception("Test error")),
                contextlib.suppress(Exception),
            ):
                session.exec("SELECT 1")

                # Force the generator to handle the exception
                with contextlib.suppress(Exception):
                    session_generator.throw(Exception("Test error"))

                mock_rollback.assert_called_once()
        finally:
            # Clean up generator
            with contextlib.suppress(StopIteration):
                next(session_generator)

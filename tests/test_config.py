"""
Unit tests for application configuration.

Tests Pydantic Settings validation, environment variable loading,
and configuration utility methods.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

            assert settings.app_name == "urbaniq"
            assert settings.app_version == "0.1.0"
            assert settings.environment == "development"
            assert settings.log_level == "INFO"
            assert settings.host == "127.0.0.1"
            assert settings.port == 8000
            assert settings.debug is False

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "test-app",
                "APP_VERSION": "1.0.0",
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "DEBUG",
                "DEBUG": "true",
            },
        ):
            settings = Settings()

            assert settings.app_name == "test-app"
            assert settings.app_version == "1.0.0"
            assert settings.environment == "production"
            assert settings.log_level == "DEBUG"
            assert settings.debug is True

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log level
        settings = Settings(log_level="ERROR")
        assert settings.log_level == "ERROR"

        # Invalid log level
        with pytest.raises(ValueError, match="log_level must be one of"):
            Settings(log_level="INVALID")

    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "production", "testing"]:
            settings = Settings(environment=env)
            assert settings.environment == env

        # Invalid environment
        with pytest.raises(ValueError, match="environment must be one of"):
            Settings(environment="invalid")

    def test_environment_properties(self):
        """Test environment helper properties."""
        dev_settings = Settings(environment="development")
        prod_settings = Settings(environment="production")

        assert dev_settings.is_development is True
        assert dev_settings.is_production is False

        assert prod_settings.is_development is False
        assert prod_settings.is_production is True

    def test_log_level_int_property(self):
        """Test log level integer property."""
        import logging

        settings = Settings(log_level="DEBUG")
        assert settings.log_level_int == logging.DEBUG

        settings = Settings(log_level="INFO")
        assert settings.log_level_int == logging.INFO

    def test_ensure_directories(self):
        """Test directory creation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            settings = Settings(
                temp_dir=str(temp_path / "temp"),
                export_dir=str(temp_path / "exports"),
                cache_dir=str(temp_path / "cache"),
            )

            # Directories should not exist yet
            assert not (temp_path / "temp").exists()
            assert not (temp_path / "exports").exists()
            assert not (temp_path / "cache").exists()

            # Create directories
            settings.ensure_directories()

            # Directories should exist now
            assert (temp_path / "temp").exists()
            assert (temp_path / "exports").exists()
            assert (temp_path / "cache").exists()

    def test_cors_origins_parsing(self):
        """Test CORS origins configuration."""
        settings = Settings()

        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) == 2
        assert "http://localhost:3000" in settings.cors_origins

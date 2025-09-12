"""
Application configuration management using Pydantic Settings.

Handles environment variable loading, validation, and provides
typed configuration objects for the entire application.
"""

import logging
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="urbaniq", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: str = Field(
        default="sqlite:///./data/urbaniq.db",
        description="Database connection URL",
    )

    # Server
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload on changes")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # Future service integrations (placeholders)
    google_api_key: str = Field(default="", description="Google Gemini API key")

    # File paths
    temp_dir: str = Field(default="./data/temp", description="Temporary files")
    export_dir: str = Field(default="./data/exports", description="Export files")
    cache_dir: str = Field(default="./data/cache", description="Cache files")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is development or production."""
        valid_envs = ["development", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v.lower()

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [self.temp_dir, self.export_dir, self.cache_dir]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def log_level_int(self) -> int:
        """Get logging level as integer."""
        level = getattr(logging, self.log_level)
        return int(level)


# Global settings instance
settings = Settings()

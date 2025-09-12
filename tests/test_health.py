"""
Unit and integration tests for health check endpoint.

Tests health endpoint functionality, database connectivity checks,
and response format validation.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint_success(self, client):
        """Test successful health check response."""
        with patch("app.api.health.check_database_connection", return_value=True):
            response = client.get("/api/health")

            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ok"
            assert "timestamp" in data
            assert data["version"] == "0.1.0"
            assert data["environment"] == "development"
            assert "services" in data

            # Check services structure
            services = data["services"]
            assert "database" in services
            assert "configuration" in services

            assert services["database"]["status"] == "ok"
            assert services["configuration"]["status"] == "ok"

    def test_health_endpoint_database_error(self, client):
        """Test health check with database connection error."""
        with patch("app.api.health.check_database_connection", return_value=False):
            response = client.get("/api/health")

            assert response.status_code == 503

            data = response.json()
            assert "detail" in data
            assert data["detail"]["status"] == "error"
            assert "Database connectivity check failed" in data["detail"]["message"]

    def test_health_endpoint_response_headers(self, client):
        """Test health endpoint response headers."""
        with patch("app.api.health.check_database_connection", return_value=True):
            response = client.get("/api/health")

            assert response.status_code == 200
            assert "X-Correlation-ID" in response.headers

            # Correlation ID should be a UUID
            correlation_id = response.headers["X-Correlation-ID"]
            assert len(correlation_id) == 36  # UUID length
            assert "-" in correlation_id

    def test_health_endpoint_service_details(self, client):
        """Test detailed service information in health response."""
        with patch("app.api.health.check_database_connection", return_value=True):
            response = client.get("/api/health")

            assert response.status_code == 200
            data = response.json()

            # Database service details
            db_service = data["services"]["database"]
            assert db_service["status"] == "ok"
            assert db_service["type"] == "sqlite"

            # Configuration service details
            config_service = data["services"]["configuration"]
            assert config_service["status"] == "ok"
            assert config_service["environment"] == "development"

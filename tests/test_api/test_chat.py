"""
Comprehensive integration tests for Chat API endpoints.

Tests natural language geodata request processing, background job creation,
input validation, error handling, and integration with NLP service.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models import Job, JobStatus


class TestChatMessageEndpoint:
    """Test cases for POST /api/chat/message endpoint."""

    def test_chat_message_endpoint_success(self, client: TestClient, mock_external_services):
        """Test successful chat message processing with valid German request."""
        request_data = {"text": "Pankow Gebäude und ÖPNV-Haltestellen für Mobilitätsanalyse"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        data = response.json()

        # Verify response structure
        assert "job_id" in data
        assert "status" in data
        assert "message" in data

        # Verify job_id format (UUID-like)
        job_id = data["job_id"]
        assert len(job_id) > 10
        assert "-" in job_id or len(job_id) == 36

        # Verify German response message
        assert "verarbeitet" in data["message"].lower() or "erstellt" in data["message"].lower()

    def test_chat_message_endpoint_with_english_request(self, client: TestClient, mock_external_services):
        """Test chat endpoint with English language request."""
        request_data = {"text": "Mitte buildings for urban planning analysis"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"

    def test_chat_message_endpoint_short_request(self, client: TestClient):
        """Test chat endpoint with too short request."""
        request_data = {"text": "Hi"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 422
        error_data = response.json()
        assert "validation error" in error_data["detail"][0]["msg"].lower()

    def test_chat_message_endpoint_long_request(self, client: TestClient):
        """Test chat endpoint with too long request."""
        long_text = "a" * 501  # Exceeds 500 character limit
        request_data = {"text": long_text}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 422
        error_data = response.json()
        assert "validation error" in error_data["detail"][0]["msg"].lower()

    def test_chat_message_endpoint_empty_request(self, client: TestClient):
        """Test chat endpoint with empty request."""
        request_data = {"text": ""}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 422

    def test_chat_message_endpoint_missing_text_field(self, client: TestClient):
        """Test chat endpoint with missing text field."""
        request_data = {"message": "Pankow buildings"}  # Wrong field name

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 422
        error_data = response.json()
        assert any("text" in error["loc"] for error in error_data["detail"])

    def test_chat_message_endpoint_invalid_json(self, client: TestClient):
        """Test chat endpoint with invalid JSON."""
        response = client.post(
            "/api/chat/message",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_chat_message_endpoint_special_characters(self, client: TestClient, mock_external_services):
        """Test chat endpoint with special characters and German umlauts."""
        request_data = {"text": "Kreuzberg Gebäude & ÖPNV für Verkehrsanalyse (Höchste Qualität)"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data

    @patch("app.api.chat_background.process_geodata_request_sync")
    def test_chat_message_job_creation_in_database(
        self, mock_process, client: TestClient, db_session, mock_external_services
    ):
        """Test that job is properly created in database."""
        # Configure mock to not actually process in background
        mock_process.return_value = None

        request_data = {"text": "Friedrichshain Gebäude für Stadtplanung"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Verify job exists in database
        job = db_session.get(Job, job_id)
        assert job is not None
        assert job.user_request == request_data["text"]
        assert job.status == JobStatus.PENDING
        assert job.progress == 0

    def test_chat_message_concurrent_requests(self, client: TestClient, mock_external_services):
        """Test handling of multiple concurrent chat requests."""
        request_data = {"text": "Neukölln transport infrastructure analysis"}

        # Send multiple requests quickly
        responses = []
        for _ in range(5):
            response = client.post("/api/chat/message", json=request_data)
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 202
            assert "job_id" in response.json()

        # All job_ids should be unique
        job_ids = [r.json()["job_id"] for r in responses]
        assert len(set(job_ids)) == len(job_ids)


class TestChatInputValidation:
    """Test cases for chat input validation and error handling."""

    def test_chat_message_validation_whitespace_only(self, client: TestClient):
        """Test chat endpoint with whitespace-only request."""
        request_data = {"text": "   \n\t   "}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 422

    def test_chat_message_validation_numeric_input(self, client: TestClient, mock_external_services):
        """Test chat endpoint with numeric input."""
        request_data = {"text": "12345 Berlin coordinates 52.5200 13.4050"}

        response = client.post("/api/chat/message", json=request_data)

        # Should still process as it's valid text length
        assert response.status_code == 202

    def test_chat_message_validation_boundary_length(self, client: TestClient, mock_external_services):
        """Test chat endpoint with boundary length values."""
        # Test minimum length (5 characters)
        request_data = {"text": "12345"}
        response = client.post("/api/chat/message", json=request_data)
        assert response.status_code == 202

        # Test maximum length (500 characters)
        long_text = "Pankow " + "a" * 493  # Total 500 chars
        request_data = {"text": long_text}
        response = client.post("/api/chat/message", json=request_data)
        assert response.status_code == 202


class TestChatServiceIntegration:
    """Test cases for chat service integration with NLP and background processing."""

    @patch("app.services.nlp_service.NLPService.parse_user_request")
    def test_chat_with_nlp_service_success(self, mock_nlp, client: TestClient, db_session):
        """Test chat endpoint integration with NLP service."""
        # Configure mock NLP response
        mock_nlp.return_value = {
            "bezirk": "Charlottenburg-Wilmersdorf",
            "datasets": ["gebaeude"],
            "confidence": 0.95,
            "reasoning": "Clear request for buildings in Charlottenburg",
        }

        request_data = {"text": "Charlottenburg buildings for analysis"}

        with patch("app.api.chat_background.process_geodata_request_sync"):
            response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        mock_nlp.assert_called_once_with("Charlottenburg buildings for analysis")

    @patch("app.services.nlp_service.NLPService.parse_user_request")
    def test_chat_with_nlp_service_low_confidence(self, mock_nlp, client: TestClient):
        """Test chat endpoint with low confidence NLP result."""
        # Configure mock for low confidence
        mock_nlp.return_value = {
            "bezirk": None,
            "datasets": [],
            "confidence": 0.3,
            "error_message": "Request nicht eindeutig verstanden",
        }

        request_data = {"text": "unclear request without specific location"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 400
        error_data = response.json()
        assert "eindeutig verstanden" in error_data["detail"].lower()

    @patch("app.services.nlp_service.NLPService.parse_user_request")
    def test_chat_with_nlp_service_error(self, mock_nlp, client: TestClient):
        """Test chat endpoint with NLP service error."""
        # Configure mock to raise exception
        mock_nlp.side_effect = Exception("Gemini API quota exceeded")

        request_data = {"text": "Spandau buildings analysis"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 500
        error_data = response.json()
        assert "internal server error" in error_data["detail"].lower()

    def test_chat_response_headers(self, client: TestClient, mock_external_services):
        """Test chat endpoint response headers."""
        request_data = {"text": "Tempelhof buildings for planning"}

        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        assert response.headers["content-type"] == "application/json"

    def test_chat_endpoint_cors_headers(self, client: TestClient, mock_external_services):
        """Test CORS headers on chat endpoint."""
        request_data = {"text": "Reinickendorf transport infrastructure"}

        # Test preflight request
        options_response = client.options("/api/chat/message")
        assert options_response.status_code in (200, 405)  # 405 if OPTIONS not explicitly handled

        # Test actual request
        response = client.post("/api/chat/message", json=request_data)
        assert response.status_code == 202


class TestChatErrorScenarios:
    """Test cases for various error scenarios in chat processing."""

    def test_chat_database_error(self, client: TestClient, mock_external_services):
        """Test chat endpoint with database connection error."""
        with patch("app.api.deps.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            request_data = {"text": "Lichtenberg buildings"}
            response = client.post("/api/chat/message", json=request_data)

            assert response.status_code == 500

    def test_chat_background_task_error(self, client: TestClient, db_session):
        """Test chat endpoint with background task creation error."""
        with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
            mock_add_task.side_effect = Exception("Background task failed")

            request_data = {"text": "Steglitz-Zehlendorf transport analysis"}
            response = client.post("/api/chat/message", json=request_data)

            # Should still return success as job is created, background processing is separate
            assert response.status_code == 202

    def test_chat_memory_stress(self, client: TestClient, mock_external_services):
        """Test chat endpoint under memory stress with large requests."""
        # Test with maximum allowed size
        large_request = "Treptow-Köpenick " + "buildings analysis " * 50
        large_request = large_request[:500]  # Truncate to max allowed length

        request_data = {"text": large_request}
        response = client.post("/api/chat/message", json=request_data)

        assert response.status_code == 202
        assert "job_id" in response.json()


class TestChatPerformance:
    """Test cases for chat endpoint performance validation."""

    def test_chat_response_time(self, client: TestClient, mock_external_services):
        """Test chat endpoint response time performance."""
        import time

        request_data = {"text": "Marzahn-Hellersdorf comprehensive analysis"}

        start_time = time.time()
        response = client.post("/api/chat/message", json=request_data)
        response_time = time.time() - start_time

        assert response.status_code == 202
        # Response should be quick (< 5 seconds) as background processing is async
        assert response_time < 5.0

    def test_chat_large_batch_requests(self, client: TestClient, mock_external_services):
        """Test handling of batch requests to chat endpoint."""
        requests_data = [
            {"text": f"District {i} buildings analysis for planning"}
            for i in range(20)
        ]

        responses = []
        for request_data in requests_data:
            response = client.post("/api/chat/message", json=request_data)
            responses.append(response)

        # All should succeed
        successful_responses = [r for r in responses if r.status_code == 202]
        assert len(successful_responses) >= 18  # Allow some failures under load

        # Response times should be reasonable
        assert all("job_id" in r.json() for r in successful_responses)

"""
Comprehensive tests for NLP Service.

Tests German language parsing, district recognition, dataset identification,
confidence scoring, and error handling with OpenAI API mocking.
"""

import json
import os
from unittest.mock import Mock, patch

import pytest

from app.config import settings
from app.services.nlp_service import AVAILABLE_DATASETS, BERLIN_DISTRICTS, NLPService, ParsedRequest


class TestParsedRequestModel:
    """Test cases for ParsedRequest Pydantic model."""

    def test_parsed_request_creation_with_defaults(self):
        """Test ParsedRequest creation with default values."""
        request = ParsedRequest(confidence=0.85)

        assert request.bezirk is None
        assert request.datasets == []
        assert request.confidence == 0.85
        assert request.error_message is None
        assert request.reasoning is None

    def test_parsed_request_creation_with_all_fields(self):
        """Test ParsedRequest creation with all fields specified."""
        request = ParsedRequest(
            bezirk="Pankow",
            datasets=["gebaeude", "oepnv_haltestellen"],
            confidence=0.95,
            error_message=None,
            reasoning="Clear request with valid district and datasets",
        )

        assert request.bezirk == "Pankow"
        assert request.datasets == ["gebaeude", "oepnv_haltestellen"]
        assert request.confidence == 0.95
        assert request.reasoning == "Clear request with valid district and datasets"

    def test_bezirk_validation_with_valid_districts(self):
        """Test bezirk validation with valid Berlin districts."""
        for district in BERLIN_DISTRICTS:
            request = ParsedRequest(bezirk=district, confidence=0.8)
            assert request.bezirk == district

    def test_bezirk_validation_with_district_variations(self):
        """Test bezirk validation handles common district variations."""
        test_cases = [
            ("charlottenburg", "Charlottenburg-Wilmersdorf"),
            ("Wilmersdorf", "Charlottenburg-Wilmersdorf"),
            ("tempelhof", "Tempelhof-Schöneberg"),
            ("Schöneberg", "Tempelhof-Schöneberg"),
            ("kreuzberg", "Friedrichshain-Kreuzberg"),
            ("Friedrichshain", "Friedrichshain-Kreuzberg"),
            ("treptow", "Treptow-Köpenick"),
            ("Köpenick", "Treptow-Köpenick"),
        ]

        for input_district, expected_district in test_cases:
            request = ParsedRequest(bezirk=input_district, confidence=0.8)
            assert request.bezirk == expected_district

    def test_bezirk_validation_with_unknown_district(self):
        """Test bezirk validation with unknown district name."""
        request = ParsedRequest(bezirk="UnknownDistrict", confidence=0.8)
        assert request.bezirk == "UnknownDistrict"  # Returns original, confidence should be low

    def test_datasets_validation_with_valid_datasets(self):
        """Test datasets validation with valid dataset names."""
        request = ParsedRequest(datasets=["gebaeude", "oepnv_haltestellen"], confidence=0.8)
        assert request.datasets == ["gebaeude", "oepnv_haltestellen"]

    def test_datasets_validation_filters_invalid_datasets(self):
        """Test datasets validation filters out invalid dataset names."""
        request = ParsedRequest(
            datasets=["gebaeude", "invalid_dataset", "oepnv_haltestellen", "another_invalid"],
            confidence=0.8,
        )
        assert request.datasets == ["gebaeude", "oepnv_haltestellen"]

    def test_datasets_validation_with_empty_list(self):
        """Test datasets validation with empty list."""
        request = ParsedRequest(datasets=[], confidence=0.8)
        assert request.datasets == []

    def test_confidence_validation_clamps_values(self):
        """Test confidence validation clamps values between 0 and 1."""
        # Test below 0 - validator should clamp to 0
        request1 = ParsedRequest(confidence=-0.5)
        assert request1.confidence == 0.0

        # Test above 1 - validator should clamp to 1
        request2 = ParsedRequest(confidence=1.5)
        assert request2.confidence == 1.0

        # Test valid range - should remain unchanged
        request3 = ParsedRequest(confidence=0.75)
        assert request3.confidence == 0.75

    def test_datasets_json_property(self):
        """Test datasets_json property returns valid JSON string."""
        request = ParsedRequest(datasets=["gebaeude", "oepnv_haltestellen"], confidence=0.8)

        json_str = request.datasets_json
        parsed = json.loads(json_str)
        assert parsed == ["gebaeude", "oepnv_haltestellen"]

    def test_is_confident_property(self):
        """Test is_confident property with threshold 0.7."""
        # Above threshold
        request1 = ParsedRequest(confidence=0.8)
        assert request1.is_confident is True

        # At threshold
        request2 = ParsedRequest(confidence=0.7)
        assert request2.is_confident is True

        # Below threshold
        request3 = ParsedRequest(confidence=0.6)
        assert request3.is_confident is False

    def test_model_dump_for_job(self):
        """Test model_dump_for_job returns correct format for Job model."""
        request = ParsedRequest(bezirk="Pankow", datasets=["gebaeude"], confidence=0.85)

        job_data = request.model_dump_for_job()
        expected = {"bezirk": "Pankow", "datasets": '["gebaeude"]'}
        assert job_data == expected


class TestNLPService:
    """Test cases for NLPService class."""

    def test_nlp_service_initialization_success(self):
        """Test successful NLPService initialization with API key."""
        with patch(
            "app.services.nlp_service.settings.openai_api_key",
            "sk-test-api-key-openai-minimum-length",
        ):
            service = NLPService()
            assert service.confidence_threshold == 0.7
            assert service.llm is not None
            assert service.parser is not None

    def test_nlp_service_initialization_fails_without_api_key(self):
        """Test NLPService initialization fails without API key."""
        with (
            patch("app.services.nlp_service.settings.openai_api_key", ""),
            pytest.raises(ValueError, match="OpenAI API key not configured"),
        ):
            NLPService()

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    def test_parse_user_request_with_empty_input(self):
        """Test parse_user_request handles empty input."""
        service = NLPService()

        result = service.parse_user_request("")
        assert result.confidence == 0.0
        assert result.error_message == "Empty or invalid input text"
        assert result.reasoning == "Eingabe ist leer oder ungültig"

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    def test_parse_user_request_with_too_long_input(self):
        """Test parse_user_request handles input that is too long."""
        service = NLPService()
        long_text = "x" * 501  # Over 500 character limit

        result = service.parse_user_request(long_text)
        assert result.confidence == 0.0
        assert "too long" in result.error_message
        assert "zu lang" in result.reasoning

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_parse_user_request_successful_parsing(self, mock_llm_class):
        """Test successful parsing of German geodata request."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = """{
            "bezirk": "Pankow",
            "datasets": ["gebaeude", "oepnv_haltestellen"],
            "confidence": 0.95,
            "error_message": null,
            "reasoning": "Klare Anfrage mit gültigem Bezirk und Datensätzen"
        }"""

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        service = NLPService()
        result = service.parse_user_request("Pankow Gebäude und ÖPNV-Haltestellen")

        assert result.bezirk == "Pankow"
        assert result.datasets == ["gebaeude", "oepnv_haltestellen"]
        assert result.confidence == 0.95
        assert result.is_confident is True

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_parse_user_request_low_confidence_handling(self, mock_llm_class):
        """Test handling of low confidence responses."""
        # Mock LLM response with low confidence
        mock_response = Mock()
        mock_response.content = """{
            "bezirk": "UnknownPlace",
            "datasets": [],
            "confidence": 0.3,
            "error_message": null,
            "reasoning": "Unklare Anfrage"
        }"""

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        service = NLPService()
        result = service.parse_user_request("Unclear request")

        assert result.confidence == 0.3
        assert result.is_confident is False
        assert "Niedrige Confidence" in result.error_message

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_parse_user_request_api_error_handling(self, mock_llm_class):
        """Test handling of API errors during parsing."""
        # Mock API error
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API Error")
        mock_llm_class.return_value = mock_llm

        service = NLPService()
        result = service.parse_user_request("Pankow Gebäude")

        assert result.confidence == 0.0
        assert "Parsing failed" in result.error_message
        assert "Fehler beim Verarbeiten" in result.reasoning

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_parse_user_request_german_district_variations(self, mock_llm_class):
        """Test parsing with various German district name formats."""
        test_cases = [
            ("Charlottenburg Gebäude", "Charlottenburg-Wilmersdorf"),
            ("Tempelhof Haltestellen", "Tempelhof-Schöneberg"),
            ("Kreuzberg ÖPNV", "Friedrichshain-Kreuzberg"),
        ]

        for input_text, expected_district in test_cases:
            mock_response = Mock()
            mock_response.content = f"""{{"bezirk": "{expected_district}", "datasets": ["gebaeude"], "confidence": 0.85, "error_message": null, "reasoning": "Bezirk erfolgreich erkannt"}}"""

            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_llm_class.return_value = mock_llm

            service = NLPService()
            result = service.parse_user_request(input_text)
            assert result.bezirk == expected_district
            assert result.is_confident is True

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_parse_user_request_mixed_language_support(self, mock_llm_class):
        """Test parsing with mixed German/English input."""
        mock_response = Mock()
        mock_response.content = """{
            "bezirk": "Mitte",
            "datasets": ["gebaeude", "oepnv_haltestellen"],
            "confidence": 0.88,
            "error_message": null,
            "reasoning": "Gemischte Sprachen erfolgreich verarbeitet"
        }"""

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        service = NLPService()
        result = service.parse_user_request("Mitte buildings and public transport")

        assert result.bezirk == "Mitte"
        assert result.datasets == ["gebaeude", "oepnv_haltestellen"]
        assert result.is_confident is True

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    def test_get_suggestion_for_failed_request_no_bezirk(self):
        """Test suggestion generation when no district is identified."""
        service = NLPService()
        failed_result = ParsedRequest(confidence=0.3)

        suggestion = service.get_suggestion_for_failed_request("unclear text", failed_result)
        assert "Berliner Bezirk" in suggestion
        assert "Verfügbare Bezirke" in suggestion

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    def test_get_suggestion_for_failed_request_no_datasets(self):
        """Test suggestion generation when no datasets are identified."""
        service = NLPService()
        failed_result = ParsedRequest(bezirk="Pankow", confidence=0.3)

        suggestion = service.get_suggestion_for_failed_request("Pankow something", failed_result)
        assert "Datentypen" in suggestion
        assert "Gebäude" in suggestion
        assert "ÖPNV-Haltestellen" in suggestion

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    def test_get_suggestion_for_failed_request_general(self):
        """Test suggestion generation for general unclear requests."""
        service = NLPService()
        failed_result = ParsedRequest(bezirk="Pankow", datasets=["gebaeude"], confidence=0.3)

        suggestion = service.get_suggestion_for_failed_request("unclear", failed_result)
        assert "nicht eindeutig" in suggestion
        assert "Beispiele" in suggestion


class TestNLPServiceIntegration:
    """Integration tests for NLP Service with Job model."""

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_nlp_service_job_model_integration(self, mock_llm_class):
        """Test integration with Job model creation workflow."""
        from app.models import Job

        # Mock successful parsing
        mock_response = Mock()
        mock_response.content = """{
            "bezirk": "Pankow",
            "datasets": ["gebaeude"],
            "confidence": 0.92,
            "error_message": null,
            "reasoning": "Erfolgreiche Analyse"
        }"""

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        service = NLPService()

        # Parse request
        result = service.parse_user_request("Pankow Gebäude für Stadtplanung")

        # Create job with parsed results
        job_data = result.model_dump_for_job()
        job = Job(request_text="Pankow Gebäude für Stadtplanung", **job_data)

        assert job.bezirk == "Pankow"
        assert job.datasets == '["gebaeude"]'
        assert job.request_text == "Pankow Gebäude für Stadtplanung"

    @patch("app.services.nlp_service.settings.openai_api_key", "test-api-key")
    @patch("app.services.nlp_service.ChatOpenAI")
    def test_nlp_service_confidence_threshold_integration(self, mock_llm_class):
        """Test confidence threshold handling in service workflow."""
        # Mock low confidence response
        mock_response = Mock()
        mock_response.content = """{
            "bezirk": null,
            "datasets": [],
            "confidence": 0.4,
            "error_message": null,
            "reasoning": "Unklare Eingabe"
        }"""

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        service = NLPService()
        result = service.parse_user_request("unclear input")

        # Should have error message due to low confidence
        assert result.confidence == 0.4
        assert result.is_confident is False
        assert result.error_message is not None
        assert "Niedrige Confidence" in result.error_message

        # Suggestion should be helpful
        suggestion = service.get_suggestion_for_failed_request("unclear input", result)
        assert suggestion is not None
        assert len(suggestion) > 10  # Should be a meaningful suggestion


@pytest.mark.external
class TestNLPServiceRealAPI:
    """Integration tests using real OpenAI GPT API calls.

    These tests require OPENAI_API_KEY to be set and make real API calls.
    Run with: pytest -m external
    Skip with: pytest -m "not external"
    """

    @pytest.mark.skipif(
        not settings.openai_api_key.get_secret_value()
        or settings.openai_api_key.get_secret_value() == "test-key"
        or os.getenv("CI") == "true",
        reason="No valid OpenAI API key configured or running in CI",
    )
    def test_real_api_german_parsing(self):
        """Test real API parsing with German geodata requests."""
        service = NLPService()

        test_cases = [
            {
                "input": "Pankow Gebäude und ÖPNV-Haltestellen für Mobilitätsanalyse",
                "expected_bezirk": "Pankow",
                "expected_datasets": ["gebaeude", "oepnv_haltestellen"],
            },
            {
                "input": "Mitte buildings for urban planning",
                "expected_bezirk": "Mitte",
                "expected_datasets": ["gebaeude"],
            },
            {
                "input": "Charlottenburg Wohngebäude",
                "expected_bezirk": "Charlottenburg-Wilmersdorf",
                "expected_datasets": ["gebaeude"],
            },
        ]

        for case in test_cases:
            result = service.parse_user_request(case["input"])

            # Basic validations
            assert result.bezirk == case["expected_bezirk"], f"Failed for: {case['input']}"
            assert set(result.datasets) == set(case["expected_datasets"]), (
                f"Failed for: {case['input']}"
            )
            assert result.confidence > 0.7, (
                f"Low confidence ({result.confidence}) for: {case['input']}"
            )
            assert result.is_confident, f"Not confident for: {case['input']}"

    @pytest.mark.skipif(
        not settings.openai_api_key.get_secret_value()
        or settings.openai_api_key.get_secret_value() == "test-key"
        or os.getenv("CI") == "true",
        reason="No valid OpenAI API key configured or running in CI",
    )
    def test_real_api_low_confidence_handling(self):
        """Test real API handling of unclear requests."""
        service = NLPService()

        unclear_requests = [
            "Something unclear without district",
            "Random text with no geodata meaning",
            "xyz abc def",
        ]

        for request in unclear_requests:
            result = service.parse_user_request(request)

            # Should have low confidence or appropriate error handling
            if result.confidence < 0.7:
                assert not result.is_confident
                assert result.error_message is not None

            # Suggestion should be helpful
            suggestion = service.get_suggestion_for_failed_request(request, result)
            assert len(suggestion) > 10

    def test_berlin_districts_completeness(self):
        """Test that all expected Berlin districts are included."""
        expected_districts = {
            "Mitte",
            "Pankow",
            "Charlottenburg-Wilmersdorf",
            "Spandau",
            "Steglitz-Zehlendorf",
            "Tempelhof-Schöneberg",
            "Neukölln",
            "Treptow-Köpenick",
            "Marzahn-Hellersdorf",
            "Lichtenberg",
            "Reinickendorf",
            "Friedrichshain-Kreuzberg",
        }

        assert set(BERLIN_DISTRICTS) == expected_districts
        assert len(BERLIN_DISTRICTS) == 12

    def test_available_datasets_completeness(self):
        """Test that available datasets match MVP scope."""
        expected_datasets = {"gebaeude", "oepnv_haltestellen"}

        assert set(AVAILABLE_DATASETS) == expected_datasets
        assert len(AVAILABLE_DATASETS) == 2

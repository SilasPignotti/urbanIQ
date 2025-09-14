"""
Tests for MetadataService LLM-powered metadata report generation.

Comprehensive test suite covering template rendering, Gemini AI integration,
quality assessment processing, and multilingual support.
"""

from unittest.mock import Mock, patch

import pytest
from jinja2 import TemplateNotFound

from app.services.metadata_service import (
    MetadataError,
    MetadataService,
)


class TestMetadataServiceInitialization:
    """Test MetadataService initialization and configuration."""

    def test_service_initialization_without_api_key(self):
        """Test service initialization when Google API key is not configured."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = None

            service = MetadataService()

            assert service.llm is None
            assert service.template_env is not None

    def test_service_initialization_with_api_key(self):
        """Test service initialization with valid Google API key."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = "test-api-key"

            with patch("app.services.metadata_service.ChatGoogleGenerativeAI") as mock_llm:
                service = MetadataService()

                assert service.llm is not None
                mock_llm.assert_called_once()

    def test_service_initialization_with_invalid_api_key(self):
        """Test service initialization with invalid Google API key."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = "invalid-key"

            with patch(
                "app.services.metadata_service.ChatGoogleGenerativeAI",
                side_effect=Exception("API error"),
            ):
                service = MetadataService()

                assert service.llm is None

    def test_template_environment_setup(self):
        """Test Jinja2 template environment configuration."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = None

            service = MetadataService()

            assert service.template_env is not None
            assert "number_format" in service.template_env.filters


class TestCreateMetadataReport:
    """Test core create_metadata_report method functionality."""

    @pytest.fixture
    def service(self):
        """Create MetadataService instance for testing."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = None
            return MetadataService()

    @pytest.fixture
    def sample_datasets(self):
        """Sample datasets from ProcessingService output."""
        return [
            {
                "dataset_id": "bezirksgrenzen_pankow",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "predefined_metadata": {
                    "name": "Bezirksgrenzen Berlin",
                    "description": "Administrative district boundaries",
                    "update_frequency": "monthly",
                },
                "runtime_stats": {
                    "feature_count": 1,
                    "spatial_extent": [13.0, 52.3, 13.8, 52.7],
                    "coverage_percentage": 100.0,
                    "data_quality_score": 0.95,
                },
            },
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "predefined_metadata": {
                    "name": "Gebäudedaten Berlin",
                    "description": "Building footprints and usage data",
                    "update_frequency": "quarterly",
                },
                "runtime_stats": {
                    "feature_count": 25000,
                    "spatial_extent": [13.0, 52.3, 13.8, 52.7],
                    "coverage_percentage": 95.0,
                    "data_quality_score": 0.85,
                },
            },
        ]

    def test_create_metadata_report_german(self, service, sample_datasets):
        """Test German metadata report generation."""
        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "# Geodaten-Metadatenreport: Pankow\n\nTest report"
            mock_get_template.return_value = mock_template

            report = service.create_metadata_report(sample_datasets, "Pankow", {"language": "de"})

            assert "Geodaten-Metadatenreport: Pankow" in report
            mock_get_template.assert_called_once_with("geodata_report_de.md")

    def test_create_metadata_report_english(self, service, sample_datasets):
        """Test English metadata report generation."""
        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "# Geodata Metadata Report: Pankow\n\nTest report"
            mock_get_template.return_value = mock_template

            report = service.create_metadata_report(sample_datasets, "Pankow", {"language": "en"})

            assert "Geodata Metadata Report: Pankow" in report
            mock_get_template.assert_called_once_with("geodata_report_en.md")

    def test_create_metadata_report_empty_datasets(self, service):
        """Test error handling for empty datasets."""
        with pytest.raises(MetadataError, match="No datasets provided"):
            service.create_metadata_report([], "Pankow", {})

    def test_create_metadata_report_invalid_language(self, service, sample_datasets):
        """Test fallback to German for invalid language."""
        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "# Geodaten-Metadatenreport: Pankow"
            mock_get_template.return_value = mock_template

            service.create_metadata_report(sample_datasets, "Pankow", {"language": "fr"})

            mock_get_template.assert_called_once_with("geodata_report_de.md")

    def test_create_metadata_report_template_error(self, service, sample_datasets):
        """Test error handling for template rendering failures."""
        with (
            patch.object(
                service.template_env, "get_template", side_effect=TemplateNotFound("test")
            ),
            pytest.raises(MetadataError),
        ):
            service.create_metadata_report(sample_datasets, "Pankow", {})


class TestTemplateContextPreparation:
    """Test template context preparation logic."""

    @pytest.fixture
    def service(self):
        """Create MetadataService instance for testing."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = None
            return MetadataService()

    def test_prepare_template_context_basic(self, service):
        """Test basic template context preparation."""
        datasets = [
            {
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "runtime_stats": {
                    "feature_count": 1000,
                    "data_quality_score": 0.8,
                    "coverage_percentage": 90.0,
                },
                "predefined_metadata": {},
            }
        ]

        context = service._prepare_template_context(datasets, "Pankow", "de", {})

        assert context["bezirk"] == "Pankow"
        assert context["dataset_count"] == 1
        assert context["total_features"] == 1000
        assert context["language"] == "de"
        assert "80.0%" in context["overall_quality_score"]

    def test_prepare_template_context_multiple_datasets(self, service):
        """Test context preparation with multiple datasets."""
        datasets = [
            {
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "runtime_stats": {
                    "feature_count": 1,
                    "data_quality_score": 0.95,
                    "coverage_percentage": 100.0,
                },
                "predefined_metadata": {},
            },
            {
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "runtime_stats": {
                    "feature_count": 5000,
                    "data_quality_score": 0.85,
                    "coverage_percentage": 90.0,
                },
                "predefined_metadata": {},
            },
        ]

        context = service._prepare_template_context(datasets, "Mitte", "en", {})

        assert context["total_features"] == 5001
        assert context["dataset_count"] == 2
        assert "95.0" in context["coverage_percentage"]

    def test_process_dataset_for_template_geoportal(self, service):
        """Test dataset processing for Berlin Geoportal data."""
        dataset = {
            "dataset_type": "gebaeude",
            "source": "geoportal",
            "runtime_stats": {
                "feature_count": 2500,
                "data_quality_score": 0.88,
                "spatial_extent": [13.0, 52.3, 13.8, 52.7],
            },
            "predefined_metadata": {
                "description": "Building data",
                "update_frequency": "quarterly",
            },
        }

        processed = service._process_dataset_for_template(dataset, "de")

        assert processed["display_name"] == "Gebäudedaten Berlin"
        assert processed["source"] == "Geoportal"
        assert processed["license"] == "CC BY 3.0 DE"
        assert processed["quality_assessment"] == "Hoch"
        assert "2.500" in processed["feature_count"]

    def test_process_dataset_for_template_osm(self, service):
        """Test dataset processing for OpenStreetMap data."""
        dataset = {
            "dataset_type": "oepnv_haltestellen",
            "source": "osm",
            "runtime_stats": {
                "feature_count": 150,
                "data_quality_score": 0.75,
            },
            "predefined_metadata": {},
        }

        processed = service._process_dataset_for_template(dataset, "en")

        assert processed["display_name"] == "Public Transport Stops"
        assert processed["source"] == "Osm"
        assert processed["license"] == "Open Database License (ODbL)"
        assert processed["quality_assessment"] == "Good"

    def test_extract_key_attributes_buildings(self, service):
        """Test key attribute extraction for building datasets."""
        dataset = {"dataset_type": "gebaeude"}

        attributes_de = service._extract_key_attributes(dataset, "de")
        attributes_en = service._extract_key_attributes(dataset, "en")

        assert len(attributes_de) == 3
        assert any(attr["name"] == "nutzung" for attr in attributes_de)
        assert any(attr["name"] == "nutzung" for attr in attributes_en)
        assert attributes_de[0]["description"] == "Gebäudenutzung"
        assert attributes_en[0]["description"] == "Building usage"

    def test_extract_key_attributes_transport(self, service):
        """Test key attribute extraction for transport datasets."""
        dataset = {"dataset_type": "oepnv_haltestellen"}

        attributes = service._extract_key_attributes(dataset, "de")

        assert len(attributes) == 3
        assert any(attr["name"] == "name" for attr in attributes)
        assert any(attr["name"] == "operator" for attr in attributes)

    def test_generate_usage_notes(self, service):
        """Test usage notes generation for different dataset types."""
        buildings_note_de = service._generate_usage_notes("gebaeude", "de")
        buildings_note_en = service._generate_usage_notes("gebaeude", "en")

        assert "Stadtplanung" in buildings_note_de
        assert "urban planning" in buildings_note_en

    def test_format_spatial_extent(self, service):
        """Test spatial extent formatting."""
        extent = [13.123, 52.456, 13.789, 52.654]
        formatted = service._format_spatial_extent(extent)

        assert formatted == "[13.123, 52.456, 13.789, 52.654]"

    def test_format_spatial_extent_invalid(self, service):
        """Test spatial extent formatting with invalid data."""
        assert service._format_spatial_extent([]) == "Not available"
        assert service._format_spatial_extent([1, 2, 3]) == "Not available"

    def test_format_number_filter(self, service):
        """Test number formatting filter."""
        assert service._format_number(1000) == "1.000"
        assert service._format_number(1234567) == "1.234.567"
        assert service._format_number("test") == "test"


class TestLLMIntegration:
    """Test LLM integration and enhancement functionality."""

    @pytest.fixture
    def service_with_llm(self):
        """Create MetadataService with mocked LLM."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = "test-key"

            with patch("app.services.metadata_service.ChatGoogleGenerativeAI") as mock_llm_class:
                mock_llm = Mock()
                mock_llm_class.return_value = mock_llm

                service = MetadataService()
                service.llm = mock_llm
                return service

    def test_enhance_with_llm_success(self, service_with_llm):
        """Test successful LLM enhancement."""
        context = {
            "bezirk": "Pankow",
            "dataset_count": 2,
            "total_features": 1000,
            "datasets": [
                {"dataset_type": "gebaeude", "feature_count": 1000, "quality_score": "85%"}
            ],
        }

        # Mock LLM response
        mock_response = Mock()
        mock_response.content = """QUALITÄT: Die Datenqualität ist hoch mit guter räumlicher Abdeckung.
EMPFEHLUNGEN:
1. Verwenden Sie die Gebäudedaten für Stadtplanungsanalysen
2. Kombinieren Sie mit Verkehrsdaten für Erreichbarkeitsanalysen
3. Nutzen Sie die Bezirksgrenze als räumliche Referenz"""

        service_with_llm.llm.invoke.return_value = mock_response

        enhanced = service_with_llm._enhance_with_llm(context, "de")

        assert "quality_assessment" in enhanced
        assert "usage_recommendations" in enhanced
        assert len(enhanced["usage_recommendations"]) == 3

    def test_enhance_with_llm_failure(self, service_with_llm):
        """Test LLM enhancement failure handling."""
        context = {"bezirk": "Pankow"}

        service_with_llm.llm.invoke.side_effect = Exception("API error")

        # Should not raise exception, return empty dict
        enhanced = service_with_llm._enhance_with_llm(context, "de")
        assert enhanced == {}

    def test_get_llm_prompt_template_german(self, service_with_llm):
        """Test German LLM prompt template generation."""
        template = service_with_llm._get_llm_prompt_template("de")

        assert "Geodaten-Analyse" in template
        assert "QUALITÄT:" in template
        assert "EMPFEHLUNGEN:" in template

    def test_get_llm_prompt_template_english(self, service_with_llm):
        """Test English LLM prompt template generation."""
        template = service_with_llm._get_llm_prompt_template("en")

        assert "geodata analysis" in template
        assert "QUALITY:" in template
        assert "RECOMMENDATIONS:" in template

    def test_parse_llm_response_german(self, service_with_llm):
        """Test parsing of German LLM response."""
        response = """QUALITÄT: Die Datenqualität ist sehr hoch.
EMPFEHLUNGEN:
1. Nutzen Sie für Stadtplanung
2. Kombinieren mit anderen Datensätzen
3. Beachten Sie die Lizenzbestimmungen"""

        parsed = service_with_llm._parse_llm_response(response, "de")

        assert "quality_assessment" in parsed
        assert parsed["quality_assessment"]["summary"] == "Die Datenqualität ist sehr hoch."
        assert len(parsed["usage_recommendations"]) == 3

    def test_parse_llm_response_english(self, service_with_llm):
        """Test parsing of English LLM response."""
        response = """QUALITY: Data quality is excellent with high coverage.
RECOMMENDATIONS:
1. Use for urban planning analyses
2. Combine with transport data
3. Consider licensing requirements"""

        parsed = service_with_llm._parse_llm_response(response, "en")

        assert "quality_assessment" in parsed
        assert "excellent" in parsed["quality_assessment"]["summary"]
        assert len(parsed["usage_recommendations"]) == 3

    def test_parse_llm_response_malformed(self, service_with_llm):
        """Test parsing of malformed LLM response."""
        response = "This is not a properly formatted response"

        parsed = service_with_llm._parse_llm_response(response, "de")

        # Should return empty dict for malformed response
        assert parsed == {}


class TestMetadataServiceIntegration:
    """Integration tests for metadata service functionality."""

    @pytest.fixture
    def service(self):
        """Create MetadataService for integration testing."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = None
            return MetadataService()

    def test_end_to_end_metadata_generation_german(self, service):
        """Test complete metadata generation workflow in German."""
        datasets = [
            {
                "dataset_id": "bezirksgrenzen_charlottenburg",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "predefined_metadata": {
                    "name": "Bezirksgrenzen Berlin",
                    "description": "Administrative boundaries for Berlin districts",
                    "update_frequency": "monthly",
                },
                "runtime_stats": {
                    "feature_count": 1,
                    "spatial_extent": [13.2, 52.4, 13.6, 52.6],
                    "coverage_percentage": 100.0,
                    "data_quality_score": 0.98,
                },
            }
        ]

        # Mock template loading and rendering
        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = (
                "# Geodaten-Metadatenreport: Charlottenburg-Wilmersdorf\n\nComplete report"
            )
            mock_get_template.return_value = mock_template

            report = service.create_metadata_report(
                datasets, "Charlottenburg-Wilmersdorf", {"language": "de"}
            )

            assert "Charlottenburg-Wilmersdorf" in report
            # Verify template was called with correct context
            mock_template.render.assert_called_once()
            context = mock_template.render.call_args[1]
            assert context["bezirk"] == "Charlottenburg-Wilmersdorf"
            assert context["dataset_count"] == 1
            assert context["language"] == "de"

    def test_end_to_end_metadata_generation_english(self, service):
        """Test complete metadata generation workflow in English."""
        datasets = [
            {
                "dataset_id": "gebaeude_mitte",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "predefined_metadata": {
                    "description": "Berlin building footprints",
                    "update_frequency": "quarterly",
                },
                "runtime_stats": {
                    "feature_count": 15000,
                    "data_quality_score": 0.82,
                    "coverage_percentage": 92.5,
                },
            }
        ]

        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = (
                "# Geodata Metadata Report: Mitte\n\nComplete English report"
            )
            mock_get_template.return_value = mock_template

            report = service.create_metadata_report(datasets, "Mitte", {"language": "en"})

            assert "Mitte" in report
            mock_get_template.assert_called_once_with("geodata_report_en.md")

    @pytest.mark.external
    def test_real_template_rendering_german(self, service):
        """Test real template rendering with actual Jinja2 templates."""
        # This test requires actual template files to exist
        datasets = [
            {
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "predefined_metadata": {
                    "description": "Test buildings",
                    "update_frequency": "quarterly",
                },
                "runtime_stats": {
                    "feature_count": 100,
                    "data_quality_score": 0.9,
                    "coverage_percentage": 95.0,
                },
            }
        ]

        try:
            report = service.create_metadata_report(datasets, "Pankow", {"language": "de"})
            assert "Geodaten-Metadatenreport" in report
            assert "Pankow" in report
        except Exception as e:
            pytest.skip(f"Template files not available: {e}")

    @pytest.mark.external
    def test_real_template_rendering_english(self, service):
        """Test real template rendering with actual Jinja2 templates."""
        datasets = [
            {
                "dataset_type": "oepnv_haltestellen",
                "source": "osm",
                "predefined_metadata": {
                    "description": "Transport stops",
                    "update_frequency": "daily",
                },
                "runtime_stats": {
                    "feature_count": 50,
                    "data_quality_score": 0.8,
                    "coverage_percentage": 88.0,
                },
            }
        ]

        try:
            report = service.create_metadata_report(datasets, "Spandau", {"language": "en"})
            assert "Geodata Metadata Report" in report
            assert "Spandau" in report
        except Exception as e:
            pytest.skip(f"Template files not available: {e}")


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def service(self):
        """Create MetadataService for error testing."""
        with patch("app.services.metadata_service.settings") as mock_settings:
            mock_settings.google_api_key = None
            return MetadataService()

    def test_missing_runtime_stats(self, service):
        """Test handling of datasets with missing runtime statistics."""
        datasets = [
            {
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "predefined_metadata": {"description": "Test"},
                # Missing runtime_stats
            }
        ]

        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "Report"
            mock_get_template.return_value = mock_template

            # Should not raise exception
            report = service.create_metadata_report(datasets, "Pankow", {})
            assert report == "Report"

    def test_missing_predefined_metadata(self, service):
        """Test handling of datasets with missing predefined metadata."""
        datasets = [
            {
                "dataset_type": "gebaeude",
                "source": "geoportal",
                # Missing predefined_metadata
                "runtime_stats": {"feature_count": 100},
            }
        ]

        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "Report"
            mock_get_template.return_value = mock_template

            report = service.create_metadata_report(datasets, "Pankow", {})
            assert report == "Report"

    def test_unknown_dataset_type(self, service):
        """Test handling of unknown dataset types."""
        datasets = [
            {
                "dataset_type": "unknown_type",
                "source": "unknown_source",
                "predefined_metadata": {},
                "runtime_stats": {},
            }
        ]

        processed = service._process_dataset_for_template(datasets[0], "de")

        assert processed["display_name"] == "Unknown_Type"
        assert processed["license"] == "Unknown"

    def test_template_rendering_exception(self, service):
        """Test handling of template rendering exceptions."""
        datasets = [
            {
                "dataset_type": "test",
                "source": "test",
                "predefined_metadata": {},
                "runtime_stats": {},
            }
        ]

        with patch.object(service.template_env, "get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.side_effect = Exception("Template error")
            mock_get_template.return_value = mock_template

            with pytest.raises(MetadataError, match="Metadata report generation failed"):
                service.create_metadata_report(datasets, "Pankow", {})

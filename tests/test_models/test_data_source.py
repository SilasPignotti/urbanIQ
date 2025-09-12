"""
Unit tests for DataSource model.

Tests DataSource model validation, methods, and enumerations
with comprehensive edge case coverage.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from app.models import ConnectorType, DataSource, HealthStatus


class TestDataSourceModel:
    """Test cases for DataSource SQLModel."""

    def test_data_source_creation_with_required_fields(self):
        """Test DataSource creation with required fields only."""
        metadata_json = json.dumps({
            "license": "CC BY 3.0 DE",
            "update_frequency": "monthly"
        })

        data_source = DataSource(
            name="Berlin Buildings",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/s_wfs_alkis_gebaeude",
            category="administrative",
            metadata_json=metadata_json,
        )

        assert data_source.id is not None
        assert len(data_source.id) == 36  # UUID4 length
        assert data_source.name == "Berlin Buildings"
        assert data_source.description is None
        assert data_source.connector_type == ConnectorType.GEOPORTAL
        assert data_source.service_url.startswith("https://")
        assert data_source.layer_name is None
        assert data_source.category == "administrative"
        assert data_source.subcategory is None
        assert data_source.metadata_json == metadata_json
        assert data_source.active is True
        assert data_source.last_tested is None
        assert data_source.test_status is None

    def test_data_source_creation_with_all_fields(self):
        """Test DataSource creation with all fields specified."""
        metadata_json = json.dumps({
            "license": "CC BY 3.0 DE",
            "quality": "high",
            "update_frequency": "daily"
        })

        data_source = DataSource(
            name="OSM Transport Stops",
            description="Public transport stops from OpenStreetMap",
            connector_type=ConnectorType.OSM,
            service_url="https://overpass-api.de/api/interpreter",
            layer_name="public_transport",
            category="transport",
            subcategory="public_transport",
            metadata_json=metadata_json,
            active=False,
            test_status=HealthStatus.OK,
        )

        assert data_source.description == "Public transport stops from OpenStreetMap"
        assert data_source.connector_type == ConnectorType.OSM
        assert data_source.layer_name == "public_transport"
        assert data_source.subcategory == "public_transport"
        assert data_source.active is False
        assert data_source.test_status == HealthStatus.OK

    def test_service_url_validation_valid_urls(self):
        """Test service_url validation accepts valid URLs."""
        metadata_json = json.dumps({"test": "data"})

        # HTTP URL
        data_source1 = DataSource(
            name="Test Source",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="http://example.com/wfs",
            category="test",
            metadata_json=metadata_json,
        )
        assert data_source1.service_url == "http://example.com/wfs"

        # HTTPS URL
        data_source2 = DataSource(
            name="Test Source",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://example.com/wfs",
            category="test",
            metadata_json=metadata_json,
        )
        assert data_source2.service_url == "https://example.com/wfs"

    def test_service_url_validation_invalid_urls(self):
        """Test service_url validation rejects invalid URLs."""
        metadata_json = json.dumps({"test": "data"})

        with pytest.raises(ValueError, match="service_url must start with http:// or https://"):
            DataSource(
                name="Test Source",
                connector_type=ConnectorType.GEOPORTAL,
                service_url="ftp://example.com",
                category="test",
                metadata_json=metadata_json,
            )

        with pytest.raises(ValueError, match="service_url must start with http:// or https://"):
            DataSource(
                name="Test Source",
                connector_type=ConnectorType.GEOPORTAL,
                service_url="example.com",
                category="test",
                metadata_json=metadata_json,
            )

    def test_metadata_json_validation_valid_json(self):
        """Test metadata_json validation accepts valid JSON objects."""
        valid_metadata = json.dumps({
            "license": "CC BY 3.0 DE",
            "quality": "high",
            "nested": {"key": "value"}
        })

        data_source = DataSource(
            name="Test Source",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://example.com",
            category="test",
            metadata_json=valid_metadata,
        )

        assert data_source.metadata_json == valid_metadata

    def test_metadata_json_validation_invalid_json(self):
        """Test metadata_json validation rejects invalid JSON."""
        with pytest.raises(ValueError, match="metadata_json must be valid JSON"):
            DataSource(
                name="Test Source",
                connector_type=ConnectorType.GEOPORTAL,
                service_url="https://example.com",
                category="test",
                metadata_json="invalid json",
            )

    def test_metadata_json_validation_non_object_json(self):
        """Test metadata_json validation rejects non-object JSON."""
        with pytest.raises(ValueError, match="metadata_json must be a JSON object"):
            DataSource(
                name="Test Source",
                connector_type=ConnectorType.GEOPORTAL,
                service_url="https://example.com",
                category="test",
                metadata_json='["array", "not", "object"]',
            )

        with pytest.raises(ValueError, match="metadata_json must be a JSON object"):
            DataSource(
                name="Test Source",
                connector_type=ConnectorType.GEOPORTAL,
                service_url="https://example.com",
                category="test",
                metadata_json='"string not object"',
            )

    def test_get_metadata_method(self):
        """Test get_metadata method."""
        metadata_dict = {
            "license": "CC BY 3.0 DE",
            "quality": "high",
            "update_frequency": "daily"
        }
        metadata_json = json.dumps(metadata_dict)

        data_source = DataSource(
            name="Test Source",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://example.com",
            category="test",
            metadata_json=metadata_json,
        )

        result = data_source.get_metadata()
        assert result == metadata_dict
        assert isinstance(result, dict)

    @patch("app.models.data_source.datetime")
    def test_update_health_status_method(self, mock_datetime):
        """Test update_health_status method."""
        mock_now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        metadata_json = json.dumps({"test": "data"})
        data_source = DataSource(
            name="Test Source",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://example.com",
            category="test",
            metadata_json=metadata_json,
        )

        data_source.update_health_status(HealthStatus.OK)

        assert data_source.test_status == HealthStatus.OK
        assert data_source.last_tested == mock_now

    def test_is_healthy_method(self):
        """Test is_healthy method."""
        metadata_json = json.dumps({"test": "data"})
        data_source = DataSource(
            name="Test Source",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://example.com",
            category="test",
            metadata_json=metadata_json,
        )

        # Active and OK status
        data_source.active = True
        data_source.test_status = HealthStatus.OK
        assert data_source.is_healthy()

        # Active but error status
        data_source.active = True
        data_source.test_status = HealthStatus.ERROR
        assert not data_source.is_healthy()

        # Inactive but OK status
        data_source.active = False
        data_source.test_status = HealthStatus.OK
        assert not data_source.is_healthy()

        # Inactive and error status
        data_source.active = False
        data_source.test_status = HealthStatus.ERROR
        assert not data_source.is_healthy()

        # None test status
        data_source.active = True
        data_source.test_status = None
        assert not data_source.is_healthy()

    def test_get_full_service_url_geoportal(self):
        """Test get_full_service_url for Geoportal sources."""
        metadata_json = json.dumps({"test": "data"})
        data_source = DataSource(
            name="Berlin Buildings",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/",
            layer_name="fis:alkis_gebaeude",
            category="administrative",
            metadata_json=metadata_json,
        )

        result = data_source.get_full_service_url()
        expected = "https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/?service=WFS&request=GetFeature&typeName=fis:alkis_gebaeude"
        assert result == expected

    def test_get_full_service_url_geoportal_no_layer(self):
        """Test get_full_service_url for Geoportal without layer."""
        metadata_json = json.dumps({"test": "data"})
        data_source = DataSource(
            name="Berlin WFS",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/",
            category="administrative",
            metadata_json=metadata_json,
        )

        result = data_source.get_full_service_url()
        assert result == "https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/"

    def test_get_full_service_url_osm(self):
        """Test get_full_service_url for OSM sources."""
        metadata_json = json.dumps({"test": "data"})
        data_source = DataSource(
            name="OSM Transport",
            connector_type=ConnectorType.OSM,
            service_url="https://overpass-api.de/api/interpreter",
            layer_name="public_transport",
            category="transport",
            metadata_json=metadata_json,
        )

        result = data_source.get_full_service_url()
        assert result == "https://overpass-api.de/api/interpreter"

    def test_connector_type_enum_values(self):
        """Test ConnectorType enum has correct values."""
        assert ConnectorType.GEOPORTAL == "geoportal"
        assert ConnectorType.OSM == "osm"

    def test_health_status_enum_values(self):
        """Test HealthStatus enum has correct values."""
        assert HealthStatus.OK == "ok"
        assert HealthStatus.ERROR == "error"
        assert HealthStatus.TIMEOUT == "timeout"

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            DataSource()  # Missing all required fields

        with pytest.raises(ValueError):
            DataSource(
                name="Test",
                # Missing connector_type, service_url, category, metadata_json
            )

"""
Comprehensive tests for Berlin Geoportal WFS connectors.

Tests HTTP client functionality, error handling, GeoDataFrame integration,
spatial filtering, and CRS transformations with mocked and integration tests.
"""

import json
from unittest.mock import Mock, patch

import geopandas as gpd
import httpx
import pytest
from shapely.geometry import Polygon

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    InvalidParameterError,
    RateLimitError,
    ServiceUnavailableError,
)
from app.connectors.geoportal import BuildingsConnector, DistrictBoundariesConnector


class TestBaseConnector:
    """Test cases for BaseConnector abstract class."""

    class ConcreteConnector(BaseConnector):
        """Concrete implementation for testing."""

        async def test_connection(self) -> bool:
            return True

    @pytest.fixture
    def connector(self):
        """Create concrete connector instance."""
        return self.ConcreteConnector("https://example.com", timeout=10.0)

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://example.com"
        assert connector.timeout == 10.0
        assert "urbanIQ" in connector._client_config["headers"]["User-Agent"]

    def test_build_url(self, connector):
        """Test URL building from base URL and endpoint."""
        assert connector._build_url("api/v1") == "https://example.com/api/v1"
        assert connector._build_url("/api/v1") == "https://example.com/api/v1"

    @pytest.mark.asyncio
    async def test_make_request_success(self, connector):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            response = await connector._make_request("GET", "https://example.com/test")

            assert response.status_code == 200
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_invalid_parameter_error(self, connector):
        """Test HTTP 400 error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request parameters"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(InvalidParameterError, match="Invalid parameters"):
                await connector._make_request("GET", "https://example.com/test")

    @pytest.mark.asyncio
    async def test_make_request_rate_limit_error(self, connector):
        """Test HTTP 429 error handling."""
        mock_response = Mock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                await connector._make_request("GET", "https://example.com/test")

    @pytest.mark.asyncio
    async def test_make_request_service_unavailable_error(self, connector):
        """Test HTTP 5xx error handling."""
        mock_response = Mock()
        mock_response.status_code = 503

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
                await connector._make_request("GET", "https://example.com/test")

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(self, connector):
        """Test timeout error handling."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = (
                httpx.TimeoutException("Timeout")
            )

            with pytest.raises(ServiceUnavailableError, match="Request timeout"):
                await connector._make_request("GET", "https://example.com/test")

    @pytest.mark.asyncio
    async def test_get_json_success(self, connector):
        """Test JSON response parsing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            result = await connector._get_json("https://example.com/api")

            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_json_parse_error(self, connector):
        """Test JSON parsing error handling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(ConnectorError, match="Failed to parse JSON"):
                await connector._get_json("https://example.com/api")


class TestDistrictBoundariesConnector:
    """Test cases for DistrictBoundariesConnector."""

    @pytest.fixture
    def connector(self):
        """Create district boundaries connector."""
        return DistrictBoundariesConnector()

    def test_connector_initialization(self, connector):
        """Test connector initialization."""
        assert "alkis_bezirke" in connector.base_url
        assert connector.timeout == 30.0
        assert connector.layer_name == "alkis_bezirke:bezirksgrenzen"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, connector):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<?xml version='1.0'?><wfs:WFS_Capabilities></wfs:WFS_Capabilities>"

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, connector):
        """Test failed connection test."""
        with patch.object(connector, "_make_request", side_effect=ConnectorError("Failed")):
            result = await connector.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_fetch_district_boundary_success(self, connector):
        """Test successful district boundary fetching."""
        # Mock GeoJSON response for Pankow district
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[13.3, 52.5], [13.4, 52.5], [13.4, 52.6], [13.3, 52.6], [13.3, 52.5]]
                        ],
                    },
                    "properties": {"bezname": "Pankow", "schluessel": "03"},
                }
            ],
        }

        mock_response_text = json.dumps(mock_geojson)

        with patch.object(connector, "_get_text", return_value=mock_response_text):
            result = await connector.fetch_district_boundary("Pankow")

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) == 1
            assert result.crs.to_string() == "EPSG:25833"
            assert "bezname" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_district_boundary_not_found(self, connector):
        """Test district boundary fetching with empty result."""
        # Mock empty GeoJSON response
        mock_geojson = {"type": "FeatureCollection", "features": []}
        mock_response_text = json.dumps(mock_geojson)

        with patch.object(connector, "_get_text", return_value=mock_response_text), pytest.raises(ValueError, match="District 'NonExistent' not found"):
            await connector.fetch_district_boundary("NonExistent")

    @pytest.mark.asyncio
    async def test_fetch_all_districts_success(self, connector):
        """Test successful fetching of all district boundaries."""
        # Mock GeoJSON response with multiple districts
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[13.3, 52.5], [13.4, 52.5], [13.4, 52.6], [13.3, 52.6], [13.3, 52.5]]
                        ],
                    },
                    "properties": {"bezname": "Pankow", "schluessel": "03"},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[13.2, 52.4], [13.3, 52.4], [13.3, 52.5], [13.2, 52.5], [13.2, 52.4]]
                        ],
                    },
                    "properties": {"bezname": "Mitte", "schluessel": "01"},
                },
            ],
        }

        mock_response_text = json.dumps(mock_geojson)

        with patch.object(connector, "_get_text", return_value=mock_response_text):
            result = await connector.fetch_all_districts()

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) == 2
            assert result.crs.to_string() == "EPSG:25833"
            assert "bezname" in result.columns


class TestBuildingsConnector:
    """Test cases for BuildingsConnector."""

    @pytest.fixture
    def connector(self):
        """Create buildings connector."""
        return BuildingsConnector()

    @pytest.fixture
    def sample_district_gdf(self):
        """Create sample district boundary GeoDataFrame."""
        polygon = Polygon(
            [(400000, 5800000), (401000, 5800000), (401000, 5801000), (400000, 5801000)]
        )
        gdf = gpd.GeoDataFrame({"bezname": ["Test District"]}, geometry=[polygon], crs="EPSG:25833")
        return gdf

    def test_connector_initialization(self, connector):
        """Test connector initialization."""
        assert "alkis_gebaeude" in connector.base_url
        assert connector.timeout == 120.0  # Longer timeout for large datasets
        assert connector.layer_name == "alkis_gebaeude:gebaeude"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, connector):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<?xml version='1.0'?><wfs:WFS_Capabilities></wfs:WFS_Capabilities>"

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.test_connection()
            assert result is True

    def test_create_bbox_filter(self, connector, sample_district_gdf):
        """Test BBOX filter string creation."""
        bbox_str = connector._create_bbox_filter(sample_district_gdf)

        # Check format: minx,miny,maxx,maxy,EPSG:25833
        parts = bbox_str.split(",")
        assert len(parts) == 5
        assert parts[4] == "EPSG:25833"

        # Check that bounds include buffer
        minx, miny, maxx, maxy = map(float, parts[:4])
        assert minx < 400000  # Should have buffer
        assert maxx > 401000  # Should have buffer

    @pytest.mark.asyncio
    async def test_fetch_buildings_success(self, connector, sample_district_gdf):
        """Test successful buildings fetching."""
        # Mock GeoJSON response with buildings
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [400100, 5800100],
                                [400200, 5800100],
                                [400200, 5800200],
                                [400100, 5800200],
                                [400100, 5800100],
                            ]
                        ],
                    },
                    "properties": {"nutzung": "Wohngebäude", "geschosse": 3, "baujahr": 1995},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [400300, 5800300],
                                [400400, 5800300],
                                [400400, 5800400],
                                [400300, 5800400],
                                [400300, 5800300],
                            ]
                        ],
                    },
                    "properties": {"nutzung": "Bürogebäude", "geschosse": 5, "baujahr": 2000},
                },
            ],
        }

        mock_response_text = json.dumps(mock_geojson)

        with patch.object(connector, "_get_text", return_value=mock_response_text):
            result = await connector.fetch_buildings(sample_district_gdf)

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) <= 2  # May be less due to clipping
            assert result.crs.to_string() == "EPSG:25833"
            if len(result) > 0:
                assert "nutzung" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_buildings_empty_result(self, connector, sample_district_gdf):
        """Test buildings fetching with empty result."""
        mock_geojson = {"type": "FeatureCollection", "features": []}
        mock_response_text = json.dumps(mock_geojson)

        with patch.object(connector, "_get_text", return_value=mock_response_text):
            result = await connector.fetch_buildings(sample_district_gdf)

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) == 0
            assert result.crs.to_string() == "EPSG:25833"

    @pytest.mark.asyncio
    async def test_fetch_buildings_empty_district(self, connector):
        """Test buildings fetching with empty district boundary."""
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        with pytest.raises(ValueError, match="District boundary GeoDataFrame is empty"):
            await connector.fetch_buildings(empty_gdf)

    @pytest.mark.asyncio
    async def test_fetch_buildings_sample(self, connector, sample_district_gdf):
        """Test buildings sample fetching."""
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [400100, 5800100],
                                [400200, 5800100],
                                [400200, 5800200],
                                [400100, 5800200],
                                [400100, 5800100],
                            ]
                        ],
                    },
                    "properties": {"nutzung": "Wohngebäude"},
                }
            ],
        }

        mock_response_text = json.dumps(mock_geojson)

        with patch.object(connector, "_get_text", return_value=mock_response_text):
            result = await connector.fetch_buildings_sample(sample_district_gdf, max_features=100)

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) <= 100
            assert result.crs.to_string() == "EPSG:25833"


class TestGeoportalIntegration:
    """Integration tests for real WFS endpoints (marked as external)."""

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_district_boundaries_connection(self):
        """Test real connection to district boundaries WFS service."""
        connector = DistrictBoundariesConnector()

        result = await connector.test_connection()
        assert result is True

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_buildings_connection(self):
        """Test real connection to buildings WFS service."""
        connector = BuildingsConnector()

        result = await connector.test_connection()
        assert result is True

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_fetch_small_district(self):
        """Test fetching a small district boundary (integration test)."""
        connector = DistrictBoundariesConnector()

        # Use a small district like Tempelhof-Schöneberg
        result = await connector.fetch_district_boundary("Tempelhof-Schöneberg")

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 1
        assert result.crs.to_string() == "EPSG:25833"
        assert not result.empty
        assert result.geometry.is_valid.all()

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_fetch_buildings_sample(self):
        """Test fetching buildings sample from real service."""
        district_connector = DistrictBoundariesConnector()
        buildings_connector = BuildingsConnector()

        # Get small district boundary first
        district = await district_connector.fetch_district_boundary("Tempelhof-Schöneberg")

        # Fetch small sample of buildings
        result = await buildings_connector.fetch_buildings_sample(district, max_features=10)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) <= 10
        if len(result) > 0:
            assert result.crs.to_string() == "EPSG:25833"
            assert result.geometry.is_valid.all()


class TestErrorScenarios:
    """Test various error scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_connector_with_invalid_url(self):
        """Test connector behavior with invalid base URL."""
        connector = DistrictBoundariesConnector()
        connector.base_url = "https://invalid-url-that-does-not-exist.com"

        result = await connector.test_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_with_connection_error(self):
        """Test handling of connection errors."""
        connector = DistrictBoundariesConnector()

        with patch.object(connector, "_get_text", side_effect=ConnectorError("Connection failed")), pytest.raises(ConnectorError):
            await connector.fetch_district_boundary("Pankow")

    def test_crs_handling_with_different_input_crs(self):
        """Test CRS handling when input GeoDataFrame has different CRS."""
        # Create district boundary in WGS84
        polygon = Polygon([(13.3, 52.5), (13.4, 52.5), (13.4, 52.6), (13.3, 52.6)])
        district_wgs84 = gpd.GeoDataFrame(
            {"bezname": ["Test"]}, geometry=[polygon], crs="EPSG:4326"
        )

        connector = BuildingsConnector()
        bbox_str = connector._create_bbox_filter(district_wgs84)

        # Should work regardless of input CRS
        assert "EPSG:25833" in bbox_str
        assert len(bbox_str.split(",")) == 5

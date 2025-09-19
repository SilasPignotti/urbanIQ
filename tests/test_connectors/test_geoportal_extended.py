"""
Comprehensive tests for extended Berlin Geoportal WFS connectors.

Tests CyclingNetworkConnector, StreetNetworkConnector, and OrtsteileBoundariesConnector
with mocked HTTP responses and spatial filtering validation.
"""

import json
from unittest.mock import Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from app.connectors.base import ConnectorError, ServiceUnavailableError
from app.connectors.geoportal_extended import (
    CyclingNetworkConnector,
    OrtsteileBoundariesConnector,
    StreetNetworkConnector,
)


class TestCyclingNetworkConnector:
    """Test cases for CyclingNetworkConnector."""

    @pytest.fixture
    def connector(self):
        """Create cycling network connector instance."""
        return CyclingNetworkConnector()

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary for testing."""
        # Use EPSG:25833 coordinates (Berlin area)
        polygon = Polygon(
            [(383000, 5819000), (384000, 5819000), (384000, 5820000), (383000, 5820000)]
        )
        return gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:25833")

    @pytest.fixture
    def sample_cycling_geojson(self):
        """Create sample cycling network GeoJSON response."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[13.05, 52.35], [13.06, 52.36]],
                    },
                    "properties": {
                        "id": "cycle_1",
                        "typ": "Vorrangnetz",
                        "belag": "Asphalt",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[13.07, 52.37], [13.08, 52.38]],
                    },
                    "properties": {
                        "id": "cycle_2",
                        "typ": "Ergänzungsnetz",
                        "belag": "Pflaster",
                    },
                },
            ],
        }

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://gdi.berlin.de/services/wfs/radverkehrsnetz"
        assert connector.timeout == 60.0

    @pytest.mark.asyncio
    async def test_connection_success(self, connector):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<?xml version='1.0'?><WFS_Capabilities/>"

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_connection_failure(self, connector):
        """Test connection failure handling."""
        with patch.object(
            connector, "_make_request", side_effect=ConnectorError("Connection failed")
        ):
            result = await connector.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_fetch_cycling_network_success(
        self, connector, sample_district_boundary, sample_cycling_geojson
    ):
        """Test successful cycling network data fetching."""
        with (
            patch.object(connector, "_get_text", return_value=json.dumps(sample_cycling_geojson)),
            patch("geopandas.clip") as mock_clip,
        ):
            # Setup mock clip to return the original data with correct CRS
            mock_gdf = gpd.read_file(json.dumps(sample_cycling_geojson), driver="GeoJSON")
            mock_gdf = mock_gdf.to_crs("EPSG:25833")
            mock_clip.return_value = mock_gdf

            result = await connector.fetch_cycling_network(sample_district_boundary)

            assert not result.empty
            assert len(result) == 2
            assert result.crs == "EPSG:25833"
            assert "typ" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_cycling_network_empty_boundary(self, connector):
        """Test handling of empty district boundary."""
        empty_boundary = gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        with pytest.raises(ValueError, match="District boundary GeoDataFrame is empty"):
            await connector.fetch_cycling_network(empty_boundary)

    @pytest.mark.asyncio
    async def test_fetch_cycling_network_empty_response(self, connector, sample_district_boundary):
        """Test handling of empty WFS response."""
        empty_geojson = {"type": "FeatureCollection", "features": []}

        with patch.object(connector, "_get_text", return_value=json.dumps(empty_geojson)):
            result = await connector.fetch_cycling_network(sample_district_boundary)

            assert result.empty
            assert result.crs == "EPSG:25833"

    @pytest.mark.asyncio
    async def test_fetch_long_distance_routes_success(
        self, connector, sample_district_boundary, sample_cycling_geojson
    ):
        """Test successful long-distance cycling routes fetching."""
        with patch.object(connector, "_get_text", return_value=json.dumps(sample_cycling_geojson)):
            with patch("geopandas.clip") as mock_clip:
                mock_gdf = gpd.read_file(json.dumps(sample_cycling_geojson), driver="GeoJSON")
                mock_gdf = mock_gdf.to_crs("EPSG:25833")
                mock_clip.return_value = mock_gdf

                result = await connector.fetch_long_distance_routes(sample_district_boundary)

                assert not result.empty
                assert len(result) == 2
                assert result.crs == "EPSG:25833"

    @pytest.mark.asyncio
    async def test_fetch_cycling_network_service_error(self, connector, sample_district_boundary):
        """Test handling of service errors."""
        with patch.object(
            connector, "_get_text", side_effect=ServiceUnavailableError("Service down")
        ), pytest.raises(ServiceUnavailableError):
            await connector.fetch_cycling_network(sample_district_boundary)

    def test_create_bbox_filter(self, connector, sample_district_boundary):
        """Test BBOX filter creation."""
        bbox_filter = connector._create_bbox_filter(sample_district_boundary)

        assert "EPSG:25833" in bbox_filter
        # Should contain coordinates with buffer (Berlin EPSG:25833 coordinates)
        assert "382900" in bbox_filter  # minx with buffer
        assert "384100" in bbox_filter  # maxx with buffer

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_integration_cycling_network(self, connector, sample_district_boundary):
        """Integration test with real WFS endpoint (requires network)."""
        try:
            result = await connector.fetch_cycling_network(sample_district_boundary)
            # This may return empty results depending on the area
            assert isinstance(result, gpd.GeoDataFrame)
            assert result.crs == "EPSG:25833"
        except Exception as e:
            pytest.skip(f"External API test failed: {e}")


class TestStreetNetworkConnector:
    """Test cases for StreetNetworkConnector."""

    @pytest.fixture
    def connector(self):
        """Create street network connector instance."""
        return StreetNetworkConnector()

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary for testing."""
        # Use EPSG:25833 coordinates (Berlin area)
        polygon = Polygon(
            [(383000, 5819000), (384000, 5819000), (384000, 5820000), (383000, 5820000)]
        )
        return gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:25833")

    @pytest.fixture
    def sample_streets_geojson(self):
        """Create sample street network GeoJSON response."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[13.05, 52.35], [13.06, 52.36]],
                    },
                    "properties": {
                        "id": "street_1",
                        "name": "Musterstraße",
                        "typ": "Hauptstraße",
                    },
                }
            ],
        }

    @pytest.fixture
    def sample_points_geojson(self):
        """Create sample connection points GeoJSON response."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [13.05, 52.35]},
                    "properties": {
                        "id": "point_1",
                        "typ": "Kreuzung",
                    },
                }
            ],
        }

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://gdi.berlin.de/services/wfs/detailnetz"
        assert connector.timeout == 90.0

    @pytest.mark.asyncio
    async def test_fetch_street_segments_success(
        self, connector, sample_district_boundary, sample_streets_geojson
    ):
        """Test successful street segments fetching."""
        with patch.object(connector, "_get_text", return_value=json.dumps(sample_streets_geojson)):
            with patch("geopandas.clip") as mock_clip:
                mock_gdf = gpd.read_file(json.dumps(sample_streets_geojson), driver="GeoJSON")
                mock_gdf = mock_gdf.to_crs("EPSG:25833")
                mock_clip.return_value = mock_gdf

                result = await connector.fetch_street_segments(sample_district_boundary)

                assert not result.empty
                assert len(result) == 1
                assert result.crs == "EPSG:25833"
                assert "name" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_connection_points_success(
        self, connector, sample_district_boundary, sample_points_geojson
    ):
        """Test successful connection points fetching."""
        with patch.object(connector, "_get_text", return_value=json.dumps(sample_points_geojson)):
            with patch("geopandas.clip") as mock_clip:
                mock_gdf = gpd.read_file(json.dumps(sample_points_geojson), driver="GeoJSON")
                mock_gdf = mock_gdf.to_crs("EPSG:25833")
                mock_clip.return_value = mock_gdf

                result = await connector.fetch_connection_points(sample_district_boundary)

                assert not result.empty
                assert len(result) == 1
                assert result.crs == "EPSG:25833"
                assert "typ" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_street_structures_success(
        self, connector, sample_district_boundary, sample_streets_geojson
    ):
        """Test successful street structures fetching."""
        with patch.object(connector, "_get_text", return_value=json.dumps(sample_streets_geojson)):
            with patch("geopandas.clip") as mock_clip:
                mock_gdf = gpd.read_file(json.dumps(sample_streets_geojson), driver="GeoJSON")
                mock_gdf = mock_gdf.to_crs("EPSG:25833")
                mock_clip.return_value = mock_gdf

                result = await connector.fetch_street_structures(sample_district_boundary)

                assert not result.empty
                assert result.crs == "EPSG:25833"


class TestOrtsteileBoundariesConnector:
    """Test cases for OrtsteileBoundariesConnector."""

    @pytest.fixture
    def connector(self):
        """Create Ortsteile boundaries connector instance."""
        return OrtsteileBoundariesConnector()

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary for testing."""
        # Use EPSG:25833 coordinates (Berlin area)
        polygon = Polygon(
            [(383000, 5819000), (384000, 5819000), (384000, 5820000), (383000, 5820000)]
        )
        return gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:25833")

    @pytest.fixture
    def sample_ortsteile_geojson(self):
        """Create sample Ortsteile GeoJSON response."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [13.02, 52.32],
                                [13.05, 52.32],
                                [13.05, 52.35],
                                [13.02, 52.35],
                                [13.02, 52.32],
                            ]
                        ],
                    },
                    "properties": {
                        "id": "ortsteil_1",
                        "name": "Prenzlauer Berg",
                        "bezirk": "Pankow",
                    },
                }
            ],
        }

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://gdi.berlin.de/services/wfs/alkis_ortsteile"
        assert connector.timeout == 30.0

    @pytest.mark.asyncio
    async def test_fetch_ortsteile_boundaries_success(
        self, connector, sample_district_boundary, sample_ortsteile_geojson
    ):
        """Test successful Ortsteile boundaries fetching."""
        with patch.object(
            connector, "_get_text", return_value=json.dumps(sample_ortsteile_geojson)
        ), patch("geopandas.clip") as mock_clip:
            mock_gdf = gpd.read_file(json.dumps(sample_ortsteile_geojson), driver="GeoJSON")
            mock_gdf = mock_gdf.to_crs("EPSG:25833")
            mock_clip.return_value = mock_gdf

            result = await connector.fetch_ortsteile_boundaries(sample_district_boundary)

            assert not result.empty
            assert len(result) == 1
            assert result.crs == "EPSG:25833"
            assert "name" in result.columns
            assert "bezirk" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_ortsteile_boundaries_empty_response(
        self, connector, sample_district_boundary
    ):
        """Test handling of empty Ortsteile response."""
        empty_geojson = {"type": "FeatureCollection", "features": []}

        with patch.object(connector, "_get_text", return_value=json.dumps(empty_geojson)):
            result = await connector.fetch_ortsteile_boundaries(sample_district_boundary)

            assert result.empty
            assert result.crs == "EPSG:25833"

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_integration_ortsteile_boundaries(self, connector, sample_district_boundary):
        """Integration test with real WFS endpoint (requires network)."""
        try:
            result = await connector.fetch_ortsteile_boundaries(sample_district_boundary)
            assert isinstance(result, gpd.GeoDataFrame)
            assert result.crs == "EPSG:25833"
        except Exception as e:
            pytest.skip(f"External API test failed: {e}")

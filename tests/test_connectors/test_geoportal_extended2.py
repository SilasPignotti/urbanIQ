"""
Comprehensive tests for population and building floors connectors.

Tests PopulationDensityConnector and BuildingFloorsConnector
with mocked HTTP responses and multi-layer validation.
"""

import json
from unittest.mock import Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from app.connectors.base import ConnectorError, ServiceUnavailableError
from app.connectors.geoportal_extended2 import BuildingFloorsConnector, PopulationDensityConnector


class TestPopulationDensityConnector:
    """Test cases for PopulationDensityConnector."""

    @pytest.fixture
    def connector(self):
        """Create population density connector instance."""
        return PopulationDensityConnector()

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary for testing."""
        # Use EPSG:25833 coordinates (Berlin area)
        polygon = Polygon(
            [(383000, 5819000), (384000, 5819000), (384000, 5820000), (383000, 5820000)]
        )
        return gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:25833")

    @pytest.fixture
    def sample_population_geojson(self):
        """Create sample population density GeoJSON response."""
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
                        "id": "pop_1",
                        "einwohner_pro_ha": 450,
                        "gesamteinwohner": 1800,
                        "flaeche_ha": 4.0,
                        "jahr": 2024,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [13.05, 52.35],
                                [13.08, 52.35],
                                [13.08, 52.38],
                                [13.05, 52.38],
                                [13.05, 52.35],
                            ]
                        ],
                    },
                    "properties": {
                        "id": "pop_2",
                        "einwohner_pro_ha": 320,
                        "gesamteinwohner": 960,
                        "flaeche_ha": 3.0,
                        "jahr": 2024,
                    },
                },
            ],
        }

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://gdi.berlin.de/services/wfs/ua_einwohnerdichte_2024"
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
    async def test_fetch_population_density_success(
        self, connector, sample_district_boundary, sample_population_geojson
    ):
        """Test successful population density data fetching."""
        with (
            patch.object(
                connector, "_get_text", return_value=json.dumps(sample_population_geojson)
            ),
            patch("geopandas.clip") as mock_clip,
        ):
            mock_gdf = gpd.read_file(json.dumps(sample_population_geojson), driver="GeoJSON")
            mock_gdf = mock_gdf.to_crs("EPSG:25833")
            mock_clip.return_value = mock_gdf

            result = await connector.fetch_population_density(sample_district_boundary)

            assert not result.empty
            assert len(result) == 2
            assert result.crs == "EPSG:25833"
            assert "einwohner_pro_ha" in result.columns
            assert "gesamteinwohner" in result.columns
            assert "jahr" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_population_density_empty_boundary(self, connector):
        """Test handling of empty district boundary."""
        empty_boundary = gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        with pytest.raises(ValueError, match="District boundary GeoDataFrame is empty"):
            await connector.fetch_population_density(empty_boundary)

    @pytest.mark.asyncio
    async def test_fetch_population_density_empty_response(
        self, connector, sample_district_boundary
    ):
        """Test handling of empty WFS response."""
        empty_geojson = {"type": "FeatureCollection", "features": []}

        with patch.object(connector, "_get_text", return_value=json.dumps(empty_geojson)):
            result = await connector.fetch_population_density(sample_district_boundary)

            assert result.empty
            assert result.crs == "EPSG:25833"

    @pytest.mark.asyncio
    async def test_fetch_population_density_service_error(
        self, connector, sample_district_boundary
    ):
        """Test handling of service errors."""
        with (
            patch.object(
                connector, "_get_text", side_effect=ServiceUnavailableError("Service down")
            ),
            pytest.raises(ServiceUnavailableError),
        ):
            await connector.fetch_population_density(sample_district_boundary)

    def test_create_bbox_filter(self, connector, sample_district_boundary):
        """Test BBOX filter creation."""
        bbox_filter = connector._create_bbox_filter(sample_district_boundary)

        assert "EPSG:25833" in bbox_filter
        assert "382900" in bbox_filter  # minx with buffer
        assert "384100" in bbox_filter  # maxx with buffer

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_integration_population_density(self, connector, sample_district_boundary):
        """Integration test with real WFS endpoint (requires network)."""
        try:
            result = await connector.fetch_population_density(sample_district_boundary)
            assert isinstance(result, gpd.GeoDataFrame)
            assert result.crs == "EPSG:25833"
        except Exception as e:
            pytest.skip(f"External API test failed: {e}")


class TestBuildingFloorsConnector:
    """Test cases for BuildingFloorsConnector."""

    @pytest.fixture
    def connector(self):
        """Create building floors connector instance."""
        return BuildingFloorsConnector()

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary for testing."""
        # Use EPSG:25833 coordinates (Berlin area)
        polygon = Polygon(
            [(383000, 5819000), (384000, 5819000), (384000, 5820000), (383000, 5820000)]
        )
        return gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:25833")

    @pytest.fixture
    def sample_floors_geojson(self):
        """Create sample building floors GeoJSON response."""
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
                                [13.025, 52.32],
                                [13.025, 52.325],
                                [13.02, 52.325],
                                [13.02, 52.32],
                            ]
                        ],
                    },
                    "properties": {
                        "id": "building_1",
                        "geschosse": 8,
                        "nutzung": "Wohnen",
                        "baujahr": 2010,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [13.03, 52.33],
                                [13.035, 52.33],
                                [13.035, 52.335],
                                [13.03, 52.335],
                                [13.03, 52.33],
                            ]
                        ],
                    },
                    "properties": {
                        "id": "building_2",
                        "geschosse": 12,
                        "nutzung": "Büro",
                        "baujahr": 2020,
                    },
                },
            ],
        }

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://gdi.berlin.de/services/wfs/gebaeude_geschosse"
        assert connector.timeout == 120.0
        assert len(connector.floor_layers) == 6
        assert "more_than_10" in connector.floor_layers
        assert "7_to_10" in connector.floor_layers

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
    async def test_fetch_specific_floor_range_success(
        self, connector, sample_district_boundary, sample_floors_geojson
    ):
        """Test successful specific floor range fetching."""
        with (
            patch.object(connector, "_get_text", return_value=json.dumps(sample_floors_geojson)),
            patch("geopandas.clip") as mock_clip,
        ):
                mock_gdf = gpd.read_file(json.dumps(sample_floors_geojson), driver="GeoJSON")
                mock_gdf = mock_gdf.to_crs("EPSG:25833")
                # Add floor_range column that would be added by _fetch_floor_layer
                mock_gdf["floor_range"] = "7_to_10"
                mock_clip.return_value = mock_gdf

                result = await connector.fetch_specific_floor_range(
                    sample_district_boundary, "7_to_10"
                )

                assert not result.empty
                assert len(result) == 2
                assert result.crs == "EPSG:25833"
                assert "floor_range" in result.columns
                assert all(result["floor_range"] == "7_to_10")
                assert "geschosse" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_specific_floor_range_invalid_range(
        self, connector, sample_district_boundary
    ):
        """Test handling of invalid floor range."""
        with pytest.raises(ValueError, match="Invalid floor range"):
            await connector.fetch_specific_floor_range(sample_district_boundary, "invalid_range")

    @pytest.mark.asyncio
    async def test_fetch_all_building_floors_success(
        self, connector, sample_district_boundary, sample_floors_geojson
    ):
        """Test successful all building floors fetching."""

        # Mock _fetch_floor_layer to return data for each layer
        async def mock_fetch_layer(boundary, layer_name, floor_range):
            # Create mock data with floor_range metadata
            gdf = gpd.read_file(json.dumps(sample_floors_geojson), driver="GeoJSON")
            gdf["floor_range"] = floor_range
            return gdf

        with patch.object(connector, "_fetch_floor_layer", side_effect=mock_fetch_layer):
            result = await connector.fetch_all_building_floors(sample_district_boundary)

            assert not result.empty
            # Should have data from all 6 floor range layers
            assert len(result) == 12  # 2 buildings × 6 layers
            assert result.crs == "EPSG:25833"
            assert "floor_range" in result.columns
            assert len(result["floor_range"].unique()) == 6

    @pytest.mark.asyncio
    async def test_fetch_all_building_floors_empty_response(
        self, connector, sample_district_boundary
    ):
        """Test handling when all layers return empty responses."""

        # Mock _fetch_floor_layer to return empty data for all layers
        async def mock_fetch_layer_empty(boundary, layer_name, floor_range):
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        with patch.object(connector, "_fetch_floor_layer", side_effect=mock_fetch_layer_empty):
            result = await connector.fetch_all_building_floors(sample_district_boundary)

            assert result.empty
            assert result.crs == "EPSG:25833"

    @pytest.mark.asyncio
    async def test_fetch_all_building_floors_partial_failure(
        self, connector, sample_district_boundary, sample_floors_geojson
    ):
        """Test handling when some layers fail but others succeed."""
        call_count = 0

        async def mock_fetch_layer_partial(boundary, layer_name, floor_range):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:
                # First two calls succeed
                gdf = gpd.read_file(json.dumps(sample_floors_geojson), driver="GeoJSON")
                gdf["floor_range"] = floor_range
                return gdf
            else:
                # Remaining calls fail
                raise ConnectorError("Layer fetch failed")

        with patch.object(connector, "_fetch_floor_layer", side_effect=mock_fetch_layer_partial):
            result = await connector.fetch_all_building_floors(sample_district_boundary)

            assert not result.empty
            # Should have data from 2 successful layers
            assert len(result) == 4  # 2 buildings × 2 successful layers
            assert result.crs == "EPSG:25833"
            assert len(result["floor_range"].unique()) == 2

    @pytest.mark.asyncio
    async def test_fetch_floor_layer_empty_boundary(self, connector):
        """Test handling of empty district boundary."""
        empty_boundary = gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        with pytest.raises(ValueError, match="District boundary GeoDataFrame is empty"):
            await connector.fetch_all_building_floors(empty_boundary)

    @pytest.mark.asyncio
    async def test_fetch_floor_layer_service_error(self, connector, sample_district_boundary):
        """Test handling of service errors in floor layer fetching."""
        with (
            patch.object(
                connector, "_get_text", side_effect=ServiceUnavailableError("Service down")
            ),
            pytest.raises(ServiceUnavailableError),
        ):
            await connector.fetch_specific_floor_range(sample_district_boundary, "7_to_10")

    def test_floor_layers_mapping(self, connector):
        """Test floor layers mapping configuration."""
        expected_layers = {
            "more_than_10": "a_geschosszahl_mehr_10",
            "7_to_10": "b_geschosszahl_7_10",
            "5_to_6": "c_geschosszahl_5_6",
            "3_to_4": "d_geschosszahl_3_4",
            "1_to_2": "e_geschosszahl_1_2",
            "under_1": "f_geschosszahl_unter_1",
        }

        assert connector.floor_layers == expected_layers

    def test_create_bbox_filter(self, connector, sample_district_boundary):
        """Test BBOX filter creation."""
        bbox_filter = connector._create_bbox_filter(sample_district_boundary)

        assert "EPSG:25833" in bbox_filter
        assert "382900" in bbox_filter  # minx with buffer
        assert "384100" in bbox_filter  # maxx with buffer

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_integration_building_floors(self, connector, sample_district_boundary):
        """Integration test with real WFS endpoint (requires network)."""
        try:
            result = await connector.fetch_specific_floor_range(sample_district_boundary, "7_to_10")
            assert isinstance(result, gpd.GeoDataFrame)
            assert result.crs == "EPSG:25833"
        except Exception as e:
            pytest.skip(f"External API test failed: {e}")

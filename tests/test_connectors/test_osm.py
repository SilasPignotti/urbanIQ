"""
Comprehensive tests for OpenStreetMap Overpass API connector.

Tests rate limiting, query generation, JSON processing, GeoDataFrame integration,
spatial filtering, and CRS transformations with mocked and integration tests.
"""

import asyncio
import json
import time
from unittest.mock import Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from app.connectors.base import (
    RateLimitError,
    ServiceUnavailableError,
)
from app.connectors.osm import OverpassConnector, OverpassRateLimiter


class TestOverpassRateLimiter:
    """Test cases for Overpass API rate limiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with 2 requests per second."""
        return OverpassRateLimiter(max_requests_per_second=2.0)

    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization with correct configuration."""
        assert rate_limiter.max_requests_per_second == 2.0
        assert rate_limiter.min_interval == 0.5  # 1/2 = 0.5 seconds
        assert rate_limiter.last_request_time is None

    @pytest.mark.asyncio
    async def test_rate_limiter_first_request_immediate(self, rate_limiter):
        """Test that first request is immediate without delay."""
        start_time = time.time()
        await rate_limiter.acquire()
        elapsed = time.time() - start_time

        # Should be nearly immediate
        assert elapsed < 0.01
        assert rate_limiter.last_request_time is not None

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_delay(self, rate_limiter):
        """Test that rate limiter enforces proper delay between requests."""
        # First request
        await rate_limiter.acquire()
        first_time = rate_limiter.last_request_time

        # Second request should be delayed
        start_time = time.time()
        await rate_limiter.acquire()
        elapsed = time.time() - start_time

        # Should wait approximately 0.5 seconds
        assert 0.4 <= elapsed <= 0.6
        assert rate_limiter.last_request_time > first_time

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_requests(self, rate_limiter):
        """Test rate limiter handles concurrent requests correctly."""

        async def make_request():
            await rate_limiter.acquire()
            return time.time()

        start_time = time.time()

        # Make 3 concurrent requests
        results = await asyncio.gather(make_request(), make_request(), make_request())

        total_elapsed = time.time() - start_time

        # Should take at least 1 second for 3 requests (2 delays of 0.5s each)
        assert total_elapsed >= 1.0

        # Requests should be ordered by time
        assert results[0] < results[1] < results[2]


class TestOverpassConnector:
    """Test cases for OverpassConnector class."""

    @pytest.fixture
    def connector(self):
        """Create OverpassConnector instance."""
        return OverpassConnector(timeout=30.0, rate_limit_rps=10.0)  # Faster rate for tests

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary GeoDataFrame in EPSG:25833."""
        # Pankow-like boundary in Berlin coordinates
        polygon = Polygon(
            [
                (390000, 5822000),
                (400000, 5822000),
                (400000, 5832000),
                (390000, 5832000),
                (390000, 5822000),
            ]
        )

        return gpd.GeoDataFrame({"namgem": ["Pankow"]}, geometry=[polygon], crs="EPSG:25833")

    @pytest.fixture
    def sample_overpass_response(self):
        """Sample Overpass API response with transport stops in Pankow area."""
        # Coordinates that convert to be within the sample district boundary
        return {
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 52.5700,  # Pankow area coordinates
                    "lon": 13.4100,
                    "tags": {
                        "name": "Pankow Rathaus",
                        "public_transport": "stop_position",
                        "operator": "BVG",
                        "network": "VBB",
                        "ref": "900140001",
                    },
                },
                {
                    "type": "node",
                    "id": 987654321,
                    "lat": 52.5750,
                    "lon": 13.4150,
                    "tags": {"name": "Pankow Bus Stop", "highway": "bus_stop", "operator": "BVG"},
                },
                {
                    "type": "node",
                    "id": 555666777,
                    "lat": 52.5800,
                    "lon": 13.4200,
                    "tags": {"railway": "tram_stop", "name": "Pankow Tram"},
                },
            ]
        }

    def test_connector_initialization(self, connector):
        """Test connector initialization with proper configuration."""
        assert connector.base_url == "https://overpass-api.de/api/interpreter"
        assert connector.timeout == 30.0
        assert connector.overpass_timeout == 25
        assert connector.rate_limiter.max_requests_per_second == 10.0

    def test_determine_transport_mode(self, connector):
        """Test transport mode determination from OSM tags."""
        # Test public transport stop position
        tags1 = {"public_transport": "stop_position", "name": "Test Stop"}
        assert connector._determine_transport_mode(tags1) == "public_transport"

        # Test bus stop
        tags2 = {"highway": "bus_stop", "name": "Bus Stop"}
        assert connector._determine_transport_mode(tags2) == "bus"

        # Test tram stop
        tags3 = {"railway": "tram_stop", "name": "Tram Stop"}
        assert connector._determine_transport_mode(tags3) == "tram"

        # Test rail station
        tags4 = {"railway": "station", "name": "Station"}
        assert connector._determine_transport_mode(tags4) == "rail_station"

        # Test ferry terminal
        tags5 = {"amenity": "ferry_terminal", "name": "Ferry"}
        assert connector._determine_transport_mode(tags5) == "ferry"

        # Test unknown/empty
        tags6 = {"other": "value"}
        assert connector._determine_transport_mode(tags6) == "unknown"

    def test_create_bbox_filter(self, connector, sample_district_boundary):
        """Test bbox filter creation from district boundary."""
        bbox_str = connector._create_bbox_filter(sample_district_boundary)

        # Should be in format: south,west,north,east
        coords = bbox_str.split(",")
        assert len(coords) == 4

        # Coordinates should be in WGS84 range
        south, west, north, east = map(float, coords)
        assert -90 <= south <= 90
        assert -180 <= west <= 180
        assert -90 <= north <= 90
        assert -180 <= east <= 180

        # North should be greater than south, east greater than west
        assert north > south
        assert east > west

    def test_create_bbox_filter_wgs84_input(self, connector):
        """Test bbox filter with WGS84 input coordinates."""
        # Create boundary already in WGS84
        polygon = Polygon([(13.0, 52.4), (13.8, 52.4), (13.8, 52.7), (13.0, 52.7), (13.0, 52.4)])

        boundary_wgs84 = gpd.GeoDataFrame({"name": ["Berlin"]}, geometry=[polygon], crs="EPSG:4326")

        bbox_str = connector._create_bbox_filter(boundary_wgs84)
        coords = [float(x) for x in bbox_str.split(",")]

        # Should have small buffer applied
        assert coords[0] < 52.4  # south with buffer
        assert coords[1] < 13.0  # west with buffer
        assert coords[2] > 52.7  # north with buffer
        assert coords[3] > 13.8  # east with buffer

    def test_process_overpass_response(self, connector, sample_overpass_response):
        """Test processing of Overpass API JSON response."""
        features = connector._process_overpass_response(sample_overpass_response)

        assert len(features) == 3

        # Test first feature (public transport stop)
        feature1 = features[0]
        assert feature1["osm_id"] == 123456789
        assert feature1["name"] == "Pankow Rathaus"
        assert feature1["transport_mode"] == "public_transport"
        assert feature1["operator"] == "BVG"
        assert feature1["network"] == "VBB"
        assert feature1["ref"] == "900140001"
        assert isinstance(feature1["geometry"], Point)

        # Test second feature (bus stop)
        feature2 = features[1]
        assert feature2["transport_mode"] == "bus"
        assert feature2["highway"] == "bus_stop"
        assert feature2["name"] == "Pankow Bus Stop"

        # Test third feature (tram stop)
        feature3 = features[2]
        assert feature3["transport_mode"] == "tram"
        assert feature3["railway"] == "tram_stop"
        assert feature3["name"] == "Pankow Tram"

    def test_process_overpass_response_invalid_coordinates(self, connector):
        """Test handling of invalid coordinates in Overpass response."""
        invalid_response = {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 200.0,  # Invalid latitude
                    "lon": 13.4,
                    "tags": {"name": "Invalid Stop"},
                },
                {
                    "type": "node",
                    "id": 2,
                    "lat": 52.5,
                    "lon": 200.0,  # Invalid longitude
                    "tags": {"name": "Another Invalid"},
                },
                {"type": "node", "id": 3, "lat": 52.5, "lon": 13.4, "tags": {"name": "Valid Stop"}},
            ]
        }

        features = connector._process_overpass_response(invalid_response)

        # Should only process the valid feature
        assert len(features) == 1
        assert features[0]["name"] == "Valid Stop"

    def test_process_overpass_response_missing_coordinates(self, connector):
        """Test handling of elements missing coordinates."""
        response_missing_coords = {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    # Missing lat/lon
                    "tags": {"name": "No Coords"},
                },
                {
                    "type": "way",  # Not a node
                    "id": 2,
                    "tags": {"name": "Way Element"},
                },
            ]
        }

        features = connector._process_overpass_response(response_missing_coords)
        assert len(features) == 0

    def test_process_overpass_response_empty(self, connector):
        """Test handling of empty Overpass response."""
        empty_response = {"elements": []}
        features = connector._process_overpass_response(empty_response)
        assert len(features) == 0

    @pytest.mark.asyncio
    async def test_test_connection_success(self, connector):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, connector):
        """Test connection test failure."""
        with patch.object(connector, "_make_request", side_effect=Exception("Network error")):
            result = await connector.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_fetch_transport_stops_success(
        self, connector, sample_district_boundary, sample_overpass_response
    ):
        """Test successful transport stops fetching."""
        mock_response = Mock()
        mock_response.json.return_value = sample_overpass_response

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.fetch_transport_stops(sample_district_boundary)

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) == 3
            assert result.crs == "EPSG:25833"

            # Check that all required columns exist
            expected_columns = ["osm_id", "name", "operator", "transport_mode"]
            for col in expected_columns:
                assert col in result.columns

    @pytest.mark.asyncio
    async def test_fetch_transport_stops_empty_boundary(self, connector):
        """Test handling of empty district boundary."""
        empty_boundary = gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        with pytest.raises(ValueError, match="empty"):
            await connector.fetch_transport_stops(empty_boundary)

    @pytest.mark.asyncio
    async def test_fetch_transport_stops_empty_response(self, connector, sample_district_boundary):
        """Test handling of empty Overpass response."""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.fetch_transport_stops(sample_district_boundary)

            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) == 0
            assert result.crs == "EPSG:25833"

    @pytest.mark.asyncio
    async def test_fetch_transport_stops_json_decode_error(
        self, connector, sample_district_boundary
    ):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with patch.object(connector, "_make_request", return_value=mock_response), pytest.raises(ValueError, match="Invalid JSON"):
            await connector.fetch_transport_stops(sample_district_boundary)

    @pytest.mark.asyncio
    async def test_fetch_transport_stops_http_errors(self, connector, sample_district_boundary):
        """Test handling of various HTTP errors."""
        # Test rate limit error
        with patch.object(connector, "_make_request", side_effect=RateLimitError("Rate limited")), pytest.raises(RateLimitError):
            await connector.fetch_transport_stops(sample_district_boundary)

        # Test service unavailable error
        with patch.object(
            connector, "_make_request", side_effect=ServiceUnavailableError("Service down")
        ), pytest.raises(ServiceUnavailableError):
            await connector.fetch_transport_stops(sample_district_boundary)

    @pytest.mark.asyncio
    async def test_fetch_transport_stops_crs_transformation(
        self, connector, sample_overpass_response
    ):
        """Test CRS transformation from WGS84 to EPSG:25833."""
        # Create district boundary in different CRS
        polygon = Polygon([(13.0, 52.4), (13.8, 52.4), (13.8, 52.7), (13.0, 52.7), (13.0, 52.4)])

        boundary_wgs84 = gpd.GeoDataFrame({"name": ["Berlin"]}, geometry=[polygon], crs="EPSG:4326")

        mock_response = Mock()
        mock_response.json.return_value = sample_overpass_response

        with patch.object(connector, "_make_request", return_value=mock_response):
            result = await connector.fetch_transport_stops(boundary_wgs84)

            # Result should be in EPSG:25833
            assert result.crs == "EPSG:25833"

            # Coordinates should be in UTM range (roughly 300k-700k for Berlin)
            if len(result) > 0:
                bounds = result.total_bounds
                assert 200000 < bounds[0] < 800000  # minx
                assert 5000000 < bounds[1] < 6000000  # miny


# Integration tests (marked for optional execution)
class TestOverpassConnectorIntegration:
    """Integration tests with real Overpass API."""

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_overpass_connection(self):
        """Test connection to real Overpass API."""
        connector = OverpassConnector()
        result = await connector.test_connection()
        assert result is True

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_transport_stops_fetch(self):
        """Test fetching real transport stops from Overpass API."""
        from app.connectors.geoportal import DistrictBoundariesConnector

        # Get real district boundary
        district_connector = DistrictBoundariesConnector()

        # Use small district for faster testing
        try:
            district_boundary = await district_connector.fetch_district_boundary("Mitte")
        except Exception:
            pytest.skip("Berlin Geoportal not available")

        # Fetch transport stops
        osm_connector = OverpassConnector()
        transport_stops = await osm_connector.fetch_transport_stops(district_boundary)

        # Validate results
        assert isinstance(transport_stops, gpd.GeoDataFrame)
        assert transport_stops.crs == "EPSG:25833"

        if len(transport_stops) > 0:
            # Check required columns exist
            assert "name" in transport_stops.columns
            assert "transport_mode" in transport_stops.columns
            assert "geometry" in transport_stops.columns

            # Check some stops have names
            named_stops = transport_stops[transport_stops["name"] != ""]
            assert len(named_stops) > 0

    @pytest.mark.external
    @pytest.mark.asyncio
    async def test_real_rate_limiting(self):
        """Test rate limiting with real API."""
        connector = OverpassConnector(rate_limit_rps=2.0)

        # Create small test boundary
        polygon = Polygon(
            [(13.4, 52.5), (13.41, 52.5), (13.41, 52.51), (13.4, 52.51), (13.4, 52.5)]
        )

        boundary = gpd.GeoDataFrame({"name": ["Test"]}, geometry=[polygon], crs="EPSG:4326")

        # Make multiple requests and measure timing
        start_time = time.time()

        import contextlib

        for _ in range(3):
            with contextlib.suppress(Exception):
                # API errors are okay for rate limiting test
                await connector.fetch_transport_stops(boundary)

        elapsed = time.time() - start_time

        # Should take at least 1 second for 3 requests (2 delays of 0.5s)
        assert elapsed >= 1.0

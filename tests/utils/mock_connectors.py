"""
Mock connectors for isolated testing without external API dependencies.

Provides deterministic responses for Berlin Geoportal WFS and OpenStreetMap Overpass API
connectors with configurable scenarios including success and error cases.
"""

from typing import Any

import geopandas as gpd

from app.connectors.base import ConnectorError, ServiceUnavailableError

from .test_data_generator import BerlinGeodataGenerator


class MockDistrictBoundariesConnector:
    """Mock connector for Berlin district boundaries with configurable responses."""

    def __init__(self, scenario: str = "success"):
        """Initialize mock connector with test scenario.

        Args:
            scenario: Test scenario - 'success', 'empty', 'error', 'timeout'
        """
        self.scenario = scenario
        self.generator = BerlinGeodataGenerator()

    async def fetch_district_boundary(self, district_name: str) -> gpd.GeoDataFrame:
        """Mock district boundary fetching with configurable responses."""
        if self.scenario == "timeout":
            raise ConnectorError("Connection timeout to Berlin Geoportal WFS")

        if self.scenario == "error":
            raise ServiceUnavailableError("Berlin Geoportal WFS service temporarily unavailable")

        if self.scenario == "empty":
            return gpd.GeoDataFrame(columns=["bezirk_name", "geometry"], crs="EPSG:25833")

        # Success scenario - return realistic district boundary
        return self.generator.generate_district_boundary(district_name)

    async def fetch_all_districts(self) -> gpd.GeoDataFrame:
        """Mock all districts fetching."""
        if self.scenario == "error":
            raise ConnectorError("Failed to fetch district boundaries")

        # Return boundaries for all Berlin districts
        districts = [
            "Charlottenburg-Wilmersdorf",
            "Friedrichshain-Kreuzberg",
            "Lichtenberg",
            "Marzahn-Hellersdorf",
            "Mitte",
            "Neukölln",
            "Pankow",
            "Reinickendorf",
            "Spandau",
            "Steglitz-Zehlendorf",
            "Tempelhof-Schöneberg",
            "Treptow-Köpenick",
        ]

        all_boundaries = []
        for district in districts:
            boundary = self.generator.generate_district_boundary(district)
            all_boundaries.append(boundary)

        return gpd.concat(all_boundaries, ignore_index=True)

    async def test_connection(self) -> bool:
        """Mock connection test."""
        return self.scenario != "error"


class MockBuildingsConnector:
    """Mock connector for Berlin building data with realistic responses."""

    def __init__(self, scenario: str = "success", feature_count: int = 100):
        """Initialize mock connector.

        Args:
            scenario: Test scenario - 'success', 'empty', 'error', 'large_dataset'
            feature_count: Number of features to generate for testing
        """
        self.scenario = scenario
        self.feature_count = feature_count
        self.generator = BerlinGeodataGenerator()

    async def fetch_buildings(
        self,
        bbox: tuple[float, float, float, float],
        district_boundary: gpd.GeoDataFrame | None = None,
    ) -> gpd.GeoDataFrame:
        """Mock building data fetching with spatial filtering."""
        if self.scenario == "timeout":
            raise ConnectorError("WFS request timeout - server overloaded")

        if self.scenario == "error":
            raise ServiceUnavailableError("Berlin Geoportal buildings service unavailable")

        if self.scenario == "empty":
            return gpd.GeoDataFrame(
                columns=["height", "type", "year_built", "geometry"], crs="EPSG:25833"
            )

        if self.scenario == "large_dataset":
            # Simulate large dataset for performance testing
            return self.generator.generate_buildings_data(
                district="Mitte",
                count=5000,  # Large dataset
                bbox=bbox,
            )

        # Success scenario - return realistic building data
        return self.generator.generate_buildings_data(
            district="Pankow", count=self.feature_count, bbox=bbox
        )

    async def fetch_buildings_sample(self, max_features: int = 10) -> gpd.GeoDataFrame:
        """Mock sample building data fetching."""
        if self.scenario == "error":
            raise ConnectorError("Failed to fetch building sample")

        return self.generator.generate_buildings_data(
            district="Pankow", count=min(max_features, 10)
        )

    async def test_connection(self) -> bool:
        """Mock connection test."""
        return self.scenario not in ("error", "timeout")


class MockOverpassConnector:
    """Mock connector for OpenStreetMap Overpass API with rate limiting simulation."""

    def __init__(self, scenario: str = "success", feature_count: int = 50):
        """Initialize mock connector.

        Args:
            scenario: Test scenario - 'success', 'empty', 'rate_limit', 'error'
            feature_count: Number of transport stops to generate
        """
        self.scenario = scenario
        self.feature_count = feature_count
        self.generator = BerlinGeodataGenerator()
        self.request_count = 0

    async def fetch_transport_stops(
        self,
        bbox: tuple[float, float, float, float],
        district_boundary: gpd.GeoDataFrame | None = None,
    ) -> gpd.GeoDataFrame:
        """Mock transport stops fetching with rate limiting simulation."""
        self.request_count += 1

        if self.scenario == "rate_limit" and self.request_count > 2:
            raise ConnectorError("Rate limit exceeded - too many requests to Overpass API")

        if self.scenario == "timeout":
            raise ConnectorError("Overpass API query timeout - complex query or server overload")

        if self.scenario == "error":
            raise ServiceUnavailableError("Overpass API temporarily unavailable")

        if self.scenario == "empty":
            return gpd.GeoDataFrame(
                columns=["name", "transport_type", "platform", "geometry"], crs="EPSG:25833"
            )

        # Success scenario - return realistic transport stop data
        return self.generator.generate_transport_stops_data(
            district="Pankow", count=self.feature_count, bbox=bbox
        )

    async def test_connection(self) -> bool:
        """Mock connection test."""
        return self.scenario not in ("error", "timeout")

    def reset_rate_limit(self) -> None:
        """Reset rate limit counter for testing."""
        self.request_count = 0


class MockServiceHealthChecker:
    """Mock service health checker for Data Service testing."""

    def __init__(self, connector_health: dict[str, bool] | None = None):
        """Initialize health checker.

        Args:
            connector_health: Dict mapping connector names to health status
        """
        self.connector_health = connector_health or {
            "district_boundaries": True,
            "buildings": True,
            "transport_stops": True,
        }

    async def check_connector_health(self, connector_name: str) -> dict[str, Any]:
        """Mock connector health check."""
        is_healthy = self.connector_health.get(connector_name, True)

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "response_time_ms": 150 if is_healthy else None,
            "last_successful_request": "2025-09-17T10:00:00Z" if is_healthy else None,
            "error_message": None if is_healthy else "Connection refused",
        }

    async def check_all_connectors(self) -> dict[str, dict[str, Any]]:
        """Mock health check for all connectors."""
        results = {}
        for connector_name in self.connector_health:
            results[connector_name] = await self.check_connector_health(connector_name)
        return results


# Utility functions for mock setup
def create_mock_connectors(scenario: str = "success") -> dict[str, Any]:
    """Create a complete set of mock connectors for testing.

    Args:
        scenario: Global scenario for all connectors

    Returns:
        Dict containing all mock connectors
    """
    return {
        "district_boundaries": MockDistrictBoundariesConnector(scenario),
        "buildings": MockBuildingsConnector(scenario),
        "transport_stops": MockOverpassConnector(scenario),
        "health_checker": MockServiceHealthChecker(),
    }


def create_error_scenario_connectors() -> dict[str, Any]:
    """Create mock connectors configured for error testing."""
    return {
        "district_boundaries": MockDistrictBoundariesConnector("error"),
        "buildings": MockBuildingsConnector("timeout"),
        "transport_stops": MockOverpassConnector("rate_limit"),
        "health_checker": MockServiceHealthChecker(
            {
                "district_boundaries": False,
                "buildings": False,
                "transport_stops": False,
            }
        ),
    }


def create_performance_test_connectors() -> dict[str, Any]:
    """Create mock connectors for performance testing with large datasets."""
    return {
        "district_boundaries": MockDistrictBoundariesConnector("success"),
        "buildings": MockBuildingsConnector("large_dataset", feature_count=2000),
        "transport_stops": MockOverpassConnector("success", feature_count=500),
        "health_checker": MockServiceHealthChecker(),
    }

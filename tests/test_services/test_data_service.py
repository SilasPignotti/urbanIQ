"""
Comprehensive tests for Data Service.

Tests parallel data orchestration, error resilience, runtime statistics collection,
service health monitoring, and integration with existing connector infrastructure.
"""

import asyncio
from datetime import datetime
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from app.connectors import ConnectorError, ServiceUnavailableError
from app.models.job import JobStatus
from app.services.data_service import DATASET_CONNECTOR_MAPPING, DATASET_METADATA, DataService


class TestDataServiceInitialization:
    """Test cases for DataService initialization."""

    def test_data_service_initialization(self):
        """Test DataService initializes with all connector instances."""
        service = DataService()

        assert service._district_connector is not None
        assert service._buildings_connector is not None
        assert service._osm_connector is not None
        assert len(service._connector_instances) == 3
        assert "bezirksgrenzen" in service._connector_instances
        assert "gebaeude" in service._connector_instances
        assert "oepnv_haltestellen" in service._connector_instances

    def test_dataset_connector_mapping_completeness(self):
        """Test dataset connector mapping includes all required datasets."""
        expected_datasets = ["bezirksgrenzen", "gebaeude", "oepnv_haltestellen"]

        for dataset in expected_datasets:
            assert dataset in DATASET_CONNECTOR_MAPPING
            assert DATASET_CONNECTOR_MAPPING[dataset] is not None

    def test_dataset_metadata_completeness(self):
        """Test predefined metadata exists for all dataset types."""
        expected_datasets = ["bezirksgrenzen", "gebaeude", "oepnv_haltestellen"]

        for dataset in expected_datasets:
            assert dataset in DATASET_METADATA
            metadata = DATASET_METADATA[dataset]
            assert "name" in metadata
            assert "description" in metadata
            assert "license" in metadata
            assert "update_frequency" in metadata


class TestFetchDatasetsForRequest:
    """Test cases for main fetch_datasets_for_request method."""

    @pytest.fixture
    def mock_geodataframe(self):
        """Create a mock GeoDataFrame for testing."""
        geometry = [Point(13.4, 52.5), Point(13.5, 52.6)]
        gdf = gpd.GeoDataFrame({"name": ["Test1", "Test2"]}, geometry=geometry, crs="EPSG:4326")
        return gdf

    @pytest.fixture
    def mock_district_boundary(self):
        """Create a mock district boundary GeoDataFrame."""
        geometry = [Polygon([(13.0, 52.0), (14.0, 52.0), (14.0, 53.0), (13.0, 53.0)])]
        gdf = gpd.GeoDataFrame({"bezirk": ["Pankow"]}, geometry=geometry, crs="EPSG:25833")
        return gdf

    @patch("app.services.data_service.DataService._update_job_status")
    async def test_successful_parallel_fetch_all_datasets(
        self, mock_update_status, mock_geodataframe, mock_district_boundary
    ):
        """Test successful parallel fetch of all datasets."""
        service = DataService()

        # Mock all connector methods
        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                return_value=mock_district_boundary,
            ) as mock_district,
            patch.object(
                service._buildings_connector, "fetch_buildings", return_value=mock_geodataframe
            ) as mock_buildings,
            patch.object(
                service._osm_connector, "fetch_transport_stops", return_value=mock_geodataframe
            ) as mock_osm,
        ):
            result = await service.fetch_datasets_for_request(
                "Pankow", ["gebaeude", "oepnv_haltestellen"], "test_job_id"
            )

            # Verify all datasets returned
            assert len(result) == 3
            dataset_types = [ds["dataset_type"] for ds in result]
            assert "bezirksgrenzen" in dataset_types
            assert "gebaeude" in dataset_types
            assert "oepnv_haltestellen" in dataset_types

            # Verify connector calls
            mock_district.assert_called_with("Pankow")
            mock_buildings.assert_called_once()
            mock_osm.assert_called_once()

            # Verify job status updates
            assert mock_update_status.call_count >= 2

    @patch("app.services.data_service.DataService._update_job_status")
    async def test_automatic_district_boundary_inclusion(
        self, _mock_update_status, mock_district_boundary
    ):
        """Test that district boundary is always included automatically."""
        service = DataService()

        with patch.object(
            service._district_connector,
            "fetch_district_boundary",
            return_value=mock_district_boundary,
        ):
            # Request only gebaeude, but bezirksgrenzen should be included automatically
            result = await service.fetch_datasets_for_request("Pankow", ["gebaeude"], "test_job_id")

            # Verify district boundary is included
            dataset_types = [ds["dataset_type"] for ds in result]
            assert "bezirksgrenzen" in dataset_types

    async def test_district_boundary_failure_aborts_request(self, mock_geodataframe):
        """Test that district boundary failure aborts entire request."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                side_effect=ConnectorError("District fetch failed"),
            ),
            patch.object(
                service._buildings_connector, "fetch_buildings", return_value=mock_geodataframe
            ),
            patch("app.services.data_service.DataService._update_job_status") as mock_update_status,
        ):
            with pytest.raises(ConnectorError, match="Failed to fetch district boundary"):
                await service.fetch_datasets_for_request("Pankow", ["gebaeude"], "test_job_id")

            # Verify job status updated to failed
            calls = mock_update_status.call_args_list
            failed_call = None
            for call in calls:
                if call[0][1] == JobStatus.FAILED:
                    failed_call = call
                    break

            assert failed_call is not None
            assert "District boundary fetch failed" in failed_call[0][3]

    async def test_partial_failure_resilience(self, mock_geodataframe, mock_district_boundary):
        """Test that other connector failures don't abort entire request."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                return_value=mock_district_boundary,
            ),
            patch.object(
                service._buildings_connector, "fetch_buildings", return_value=mock_geodataframe
            ),
            patch.object(
                service._osm_connector,
                "fetch_transport_stops",
                side_effect=ServiceUnavailableError("OSM unavailable"),
            ),
            patch("app.services.data_service.DataService._update_job_status"),
        ):
            result = await service.fetch_datasets_for_request(
                "Pankow", ["gebaeude", "oepnv_haltestellen"], "test_job_id"
            )

            # Should return successful datasets (district + buildings)
            assert len(result) == 2
            dataset_types = [ds["dataset_type"] for ds in result]
            assert "bezirksgrenzen" in dataset_types
            assert "gebaeude" in dataset_types
            assert "oepnv_haltestellen" not in dataset_types

    async def test_unknown_dataset_handling(self, mock_district_boundary):
        """Test handling of unknown dataset types."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                return_value=mock_district_boundary,
            ),
            patch("app.services.data_service.DataService._update_job_status"),
        ):
            result = await service.fetch_datasets_for_request(
                "Pankow", ["unknown_dataset"], "test_job_id"
            )

            # Should return only district boundary
            assert len(result) == 1
            assert result[0]["dataset_type"] == "bezirksgrenzen"

    async def test_no_job_id_handling(self, mock_district_boundary):
        """Test that method works without job_id provided."""
        service = DataService()

        with patch.object(
            service._district_connector,
            "fetch_district_boundary",
            return_value=mock_district_boundary,
        ):
            result = await service.fetch_datasets_for_request("Pankow", [])

            # Should return district boundary
            assert len(result) == 1
            assert result[0]["dataset_type"] == "bezirksgrenzen"


class TestFetchSingleDataset:
    """Test cases for _fetch_single_dataset method."""

    @pytest.fixture
    def mock_geodataframe(self):
        """Create a mock GeoDataFrame with multiple features."""
        geometry = [Point(13.4, 52.5), Point(13.5, 52.6), Point(13.6, 52.7)]
        gdf = gpd.GeoDataFrame(
            {"name": ["Feature1", "Feature2", "Feature3"]}, geometry=geometry, crs="EPSG:25833"
        )
        return gdf

    async def test_fetch_district_boundary_dataset(self, mock_geodataframe):
        """Test fetching district boundary dataset."""
        service = DataService()

        with patch.object(
            service._district_connector, "fetch_district_boundary", return_value=mock_geodataframe
        ):
            result = await service._fetch_single_dataset("Pankow", "bezirksgrenzen")

            assert result["dataset_id"] == "bezirksgrenzen_pankow"
            assert result["dataset_type"] == "bezirksgrenzen"
            assert result["source"] == "geoportal"
            assert result["geodata"] is mock_geodataframe
            assert result["predefined_metadata"] == DATASET_METADATA["bezirksgrenzen"]
            assert "runtime_stats" in result

    async def test_fetch_buildings_dataset(self, mock_geodataframe):
        """Test fetching buildings dataset with district boundary dependency."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                return_value=mock_geodataframe,
            ),
            patch.object(
                service._buildings_connector, "fetch_buildings", return_value=mock_geodataframe
            ),
        ):
            result = await service._fetch_single_dataset("Pankow", "gebaeude")

            assert result["dataset_id"] == "gebaeude_pankow"
            assert result["dataset_type"] == "gebaeude"
            assert result["source"] == "geoportal"
            assert result["geodata"] is mock_geodataframe

    async def test_fetch_osm_dataset(self, mock_geodataframe):
        """Test fetching OSM transport stops dataset."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                return_value=mock_geodataframe,
            ),
            patch.object(
                service._osm_connector, "fetch_transport_stops", return_value=mock_geodataframe
            ),
        ):
            result = await service._fetch_single_dataset("Pankow", "oepnv_haltestellen")

            assert result["dataset_id"] == "oepnv_haltestellen_pankow"
            assert result["dataset_type"] == "oepnv_haltestellen"
            assert result["source"] == "osm"
            assert result["geodata"] is mock_geodataframe

    async def test_unsupported_dataset_type(self):
        """Test handling of unsupported dataset types."""
        service = DataService()

        with pytest.raises(ConnectorError, match="Unsupported dataset type"):
            await service._fetch_single_dataset("Pankow", "unsupported_type")

    async def test_connector_failure_propagation(self):
        """Test that connector failures are properly propagated."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                side_effect=ServiceUnavailableError("Service down"),
            ),
            pytest.raises(ConnectorError, match="Failed to fetch bezirksgrenzen"),
        ):
            await service._fetch_single_dataset("Pankow", "bezirksgrenzen")


class TestRuntimeStatistics:
    """Test cases for runtime statistics calculation."""

    def test_calculate_runtime_stats_with_data(self):
        """Test runtime statistics calculation with valid data."""
        service = DataService()

        # Create test GeoDataFrame
        geometry = [Point(13.4, 52.5), Point(13.5, 52.6)]
        gdf = gpd.GeoDataFrame({"name": ["Test1", "Test2"]}, geometry=geometry, crs="EPSG:25833")

        stats = service._calculate_runtime_stats(gdf, 1500.0, "success")

        assert stats["response_time_ms"] == 1500
        assert stats["feature_count"] == 2
        assert stats["spatial_extent"] is not None
        assert len(stats["spatial_extent"]) == 4  # [min_x, min_y, max_x, max_y]
        assert stats["coverage_percentage"] > 0
        assert stats["data_quality_score"] == 1.0  # All features have geometry
        assert stats["connector_status"] == "success"
        assert stats["error_message"] is None
        assert isinstance(stats["request_timestamp"], datetime)

    def test_calculate_runtime_stats_empty_data(self):
        """Test runtime statistics calculation with empty data."""
        service = DataService()

        # Create empty GeoDataFrame
        gdf = gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:25833")

        stats = service._calculate_runtime_stats(gdf, 2000.0, "failed")

        assert stats["response_time_ms"] == 2000
        assert stats["feature_count"] == 0
        assert stats["spatial_extent"] is None
        assert stats["coverage_percentage"] == 0.0
        assert stats["data_quality_score"] == 0.0
        assert stats["connector_status"] == "failed"
        assert "No features returned" in stats["error_message"]

    def test_calculate_runtime_stats_partial_geometry(self):
        """Test runtime statistics with some missing geometries."""
        service = DataService()

        # Create GeoDataFrame with missing geometry
        geometry = [Point(13.4, 52.5), None, Point(13.6, 52.7)]
        gdf = gpd.GeoDataFrame(
            {"name": ["Test1", "Test2", "Test3"]}, geometry=geometry, crs="EPSG:25833"
        )

        stats = service._calculate_runtime_stats(gdf, 1000.0, "partial")

        assert stats["feature_count"] == 3
        assert stats["data_quality_score"] == 0.67  # 2/3 features have geometry
        assert stats["connector_status"] == "partial"


class TestServiceHealthMonitoring:
    """Test cases for service health monitoring."""

    async def test_all_connectors_healthy(self):
        """Test health check when all connectors are healthy."""
        service = DataService()

        with (
            patch.object(service._district_connector, "test_connection", return_value=True),
            patch.object(service._buildings_connector, "test_connection", return_value=True),
            patch.object(service._osm_connector, "test_connection", return_value=True),
        ):
            health_status = await service.test_connector_health()

            assert health_status["district"] is True
            assert health_status["buildings"] is True
            assert health_status["osm"] is True

    async def test_partial_connector_failure(self):
        """Test health check with some connector failures."""
        service = DataService()

        with (
            patch.object(service._district_connector, "test_connection", return_value=True),
            patch.object(
                service._buildings_connector,
                "test_connection",
                side_effect=Exception("Connection failed"),
            ),
            patch.object(service._osm_connector, "test_connection", return_value=True),
        ):
            health_status = await service.test_connector_health()

            assert health_status["district"] is True
            assert health_status["buildings"] is False
            assert health_status["osm"] is True

    async def test_all_connectors_unhealthy(self):
        """Test health check when all connectors are unhealthy."""
        service = DataService()

        with (
            patch.object(
                service._district_connector, "test_connection", side_effect=Exception("Down")
            ),
            patch.object(
                service._buildings_connector, "test_connection", side_effect=Exception("Down")
            ),
            patch.object(service._osm_connector, "test_connection", side_effect=Exception("Down")),
        ):
            health_status = await service.test_connector_health()

            assert health_status["district"] is False
            assert health_status["buildings"] is False
            assert health_status["osm"] is False


class TestJobStatusUpdates:
    """Test cases for job status update integration."""

    async def test_job_status_update_logging(self):
        """Test that job status updates are properly logged."""
        service = DataService()

        # Test that method runs without error (simplified implementation)
        await service._update_job_status("test_job", JobStatus.PROCESSING, 50)
        await service._update_job_status("test_job", JobStatus.COMPLETED, 100)
        await service._update_job_status("test_job", JobStatus.FAILED, 0, "Test error")

        # In a real implementation, this would verify database updates
        # For now, we just ensure the method doesn't raise exceptions


@pytest.mark.external
class TestDataServiceIntegration:
    """Integration tests with real APIs (marked as external)."""

    async def test_real_district_boundary_integration(self):
        """Test integration with real Berlin Geoportal district boundary API."""
        service = DataService()

        try:
            result = await service.fetch_datasets_for_request("Mitte", [])
            assert len(result) == 1
            assert result[0]["dataset_type"] == "bezirksgrenzen"
            assert result[0]["runtime_stats"]["feature_count"] > 0
        except ConnectorError:
            pytest.skip("Real API not available")

    async def test_performance_parallel_vs_sequential(self):
        """Test that parallel processing is faster than sequential."""
        # This would be implemented to compare timing
        # of parallel vs sequential connector execution
        pytest.skip("Performance benchmarking test - implement when needed")

    async def test_real_connector_health_check(self):
        """Test connector health check with real APIs."""
        service = DataService()

        try:
            health_status = await service.test_connector_health()
            # At least some connectors should be healthy
            assert any(health_status.values())
        except Exception:
            pytest.skip("Real API health check not available")


class TestErrorScenarios:
    """Test cases for various error scenarios."""

    async def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                side_effect=TimeoutError("Request timeout"),
            ),
            pytest.raises(ConnectorError),
        ):
            await service._fetch_single_dataset("Pankow", "bezirksgrenzen")

    async def test_malformed_response_handling(self):
        """Test handling of malformed API responses."""
        service = DataService()

        with (
            patch.object(
                service._district_connector,
                "fetch_district_boundary",
                side_effect=ValueError("Invalid response format"),
            ),
            pytest.raises(ConnectorError),
        ):
            await service._fetch_single_dataset("Pankow", "bezirksgrenzen")

    async def test_concurrent_request_handling(self):
        """Test handling of multiple concurrent requests."""
        service = DataService()

        # Create mock GeoDataFrame
        geometry = [Point(13.4, 52.5)]
        mock_gdf = gpd.GeoDataFrame({"name": ["Test"]}, geometry=geometry, crs="EPSG:4326")

        with patch.object(
            service._district_connector, "fetch_district_boundary", return_value=mock_gdf
        ):
            # Execute multiple concurrent requests
            tasks = [
                service.fetch_datasets_for_request("Pankow", []),
                service.fetch_datasets_for_request("Mitte", []),
                service.fetch_datasets_for_request("Spandau", []),
            ]

            results = await asyncio.gather(*tasks)
            assert len(results) == 3
            assert all(
                len(result) == 1 for result in results
            )  # Each should return district boundary

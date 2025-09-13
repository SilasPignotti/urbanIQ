"""
Comprehensive tests for Processing Service.

Tests geodata harmonization including CRS standardization, spatial clipping, schema normalization,
geometry validation, quality assurance metrics, and integration with DataService output format.
"""

from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from app.services.processing_service import (
    STANDARD_SCHEMA,
    TARGET_CRS,
    ProcessingError,
    ProcessingService,
)


class TestProcessingServiceInitialization:
    """Test cases for ProcessingService initialization."""

    def test_processing_service_initialization(self):
        """Test ProcessingService initializes correctly."""
        service = ProcessingService()
        assert service is not None

    def test_constants_defined(self):
        """Test that required constants are properly defined."""
        assert TARGET_CRS == "EPSG:25833"
        assert "feature_id" in STANDARD_SCHEMA
        assert "dataset_type" in STANDARD_SCHEMA
        assert "source_system" in STANDARD_SCHEMA
        assert "bezirk" in STANDARD_SCHEMA
        assert "geometry" in STANDARD_SCHEMA
        assert "original_attributes" in STANDARD_SCHEMA


class TestHarmonizeDatasets:
    """Test cases for main harmonize_datasets method."""

    @pytest.fixture
    def sample_district_boundary(self):
        """Create sample district boundary GeoDataFrame."""
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        return gpd.GeoDataFrame(
            {"bezirk_name": ["Pankow"]},
            geometry=[polygon],
            crs=TARGET_CRS
        )

    @pytest.fixture
    def sample_buildings(self):
        """Create sample buildings GeoDataFrame."""
        geometries = [
            Point(2, 2),
            Point(5, 5),
            Point(8, 8)
        ]
        return gpd.GeoDataFrame(
            {
                "nutzung": ["Wohnen", "Buero", "Handel"],
                "geschosse": [3, 8, 2],
                "baujahr": [1980, 2010, 1995]
            },
            geometry=geometries,
            crs=TARGET_CRS
        )

    @pytest.fixture
    def sample_transport_stops(self):
        """Create sample transport stops GeoDataFrame."""
        geometries = [
            Point(3, 3),
            Point(7, 7)
        ]
        return gpd.GeoDataFrame(
            {
                "name": ["Bahnhof Pankow", "S Bornholmer Str"],
                "operator": ["DB", "S-Bahn Berlin"],
                "transport_mode": ["train", "light_rail"]
            },
            geometry=geometries,
            crs=TARGET_CRS
        )

    @pytest.fixture
    def sample_datasets(self, sample_district_boundary, sample_buildings, sample_transport_stops):
        """Create sample dataset list in DataService output format."""
        return [
            {
                "dataset_id": "bezirksgrenzen_pankow",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "geodata": sample_district_boundary,
                "predefined_metadata": {"name": "District Boundaries"},
                "runtime_stats": {"feature_count": 1}
            },
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": sample_buildings,
                "predefined_metadata": {"name": "Buildings"},
                "runtime_stats": {"feature_count": 3}
            },
            {
                "dataset_id": "oepnv_haltestellen_pankow",
                "dataset_type": "oepnv_haltestellen",
                "source": "osm",
                "geodata": sample_transport_stops,
                "predefined_metadata": {"name": "Transport Stops"},
                "runtime_stats": {"feature_count": 2}
            }
        ]

    @pytest.mark.asyncio
    async def test_harmonize_datasets_success(self, sample_datasets):
        """Test successful dataset harmonization with all processing steps."""
        service = ProcessingService()

        result = await service.harmonize_datasets(sample_datasets, "Pankow")

        # Validate return structure
        assert "harmonized_data" in result
        assert "processing_stats" in result
        assert "quality_stats" in result
        assert "processing_duration_ms" in result
        assert "target_district" in result

        # Validate harmonized data
        harmonized_gdf = result["harmonized_data"]
        assert isinstance(harmonized_gdf, gpd.GeoDataFrame)
        assert harmonized_gdf.crs == TARGET_CRS
        assert len(harmonized_gdf) == 6  # 1 district + 3 buildings + 2 transport stops

        # Validate standard schema
        for col in STANDARD_SCHEMA:
            assert col in harmonized_gdf.columns

        # Validate data content
        assert all(harmonized_gdf["bezirk"] == "Pankow")
        assert set(harmonized_gdf["dataset_type"]) == {"bezirksgrenzen", "gebaeude", "oepnv_haltestellen"}
        assert set(harmonized_gdf["source_system"]) == {"geoportal", "osm"}

        # Validate processing stats
        processing_stats = result["processing_stats"]
        assert processing_stats["datasets_processed"] == 3
        assert processing_stats["datasets_failed"] == 0
        assert processing_stats["total_features"] == 6

    @pytest.mark.asyncio
    async def test_harmonize_empty_datasets(self):
        """Test harmonization with empty dataset list."""
        service = ProcessingService()

        with pytest.raises(ValueError, match="No datasets provided"):
            await service.harmonize_datasets([], "Pankow")

    @pytest.mark.asyncio
    async def test_harmonize_missing_district_boundary(self, sample_buildings):
        """Test harmonization without district boundary dataset."""
        service = ProcessingService()

        datasets = [
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": sample_buildings,
                "predefined_metadata": {"name": "Buildings"},
                "runtime_stats": {"feature_count": 3}
            }
        ]

        with pytest.raises(ProcessingError, match="Failed to harmonize datasets"):
            await service.harmonize_datasets(datasets, "Pankow")

    @pytest.mark.asyncio
    async def test_harmonize_partial_failure(self, sample_district_boundary, sample_buildings):
        """Test harmonization with some dataset processing failures."""
        service = ProcessingService()

        # Create dataset with invalid geodata to cause processing failure
        datasets = [
            {
                "dataset_id": "bezirksgrenzen_pankow",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "geodata": sample_district_boundary,
                "predefined_metadata": {"name": "District"},
                "runtime_stats": {"feature_count": 1}
            },
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": sample_buildings,
                "predefined_metadata": {"name": "Buildings"},
                "runtime_stats": {"feature_count": 3}
            },
            {
                "dataset_id": "invalid_dataset",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": None,  # This will cause failure
                "predefined_metadata": {"name": "Invalid"},
                "runtime_stats": {"feature_count": 0}
            }
        ]

        with patch.object(service, '_process_single_dataset', side_effect=[
            sample_district_boundary,  # Success for district
            sample_buildings,  # Success for buildings
            Exception("Processing failed")  # Failure for invalid dataset
        ]):
            result = await service.harmonize_datasets(datasets, "Pankow")

            assert result["processing_stats"]["datasets_processed"] == 2
            assert result["processing_stats"]["datasets_failed"] == 1


class TestCRSStandardization:
    """Test cases for CRS transformation functionality."""

    def test_standardize_crs_already_correct(self):
        """Test CRS standardization when already correct."""
        service = ProcessingService()

        geometry = [Point(0, 0), Point(1, 1)]
        gdf = gpd.GeoDataFrame({"name": ["A", "B"]}, geometry=geometry, crs=TARGET_CRS)

        result = service._standardize_crs(gdf)

        assert result.crs == TARGET_CRS
        assert len(result) == 2

    def test_standardize_crs_transformation_needed(self):
        """Test CRS transformation from WGS84 to EPSG:25833."""
        service = ProcessingService()

        # Create GeoDataFrame in WGS84
        geometry = [Point(13.4, 52.5), Point(13.5, 52.6)]  # Berlin coordinates
        gdf = gpd.GeoDataFrame({"name": ["A", "B"]}, geometry=geometry, crs="EPSG:4326")

        result = service._standardize_crs(gdf)

        assert result.crs == TARGET_CRS
        assert len(result) == 2

        # Verify coordinates are transformed (should be much larger in UTM)
        assert result.geometry.iloc[0].x > 100000  # UTM coordinates are large

    def test_standardize_crs_missing_crs(self):
        """Test CRS handling when CRS is missing."""
        service = ProcessingService()

        geometry = [Point(0, 0), Point(1, 1)]
        gdf = gpd.GeoDataFrame({"name": ["A", "B"]}, geometry=geometry)  # No CRS

        with patch('app.services.processing_service.logger') as mock_logger:
            result = service._standardize_crs(gdf)

            assert result.crs == TARGET_CRS
            mock_logger.warning.assert_called_once()

    def test_standardize_crs_empty_dataframe(self):
        """Test CRS standardization with empty GeoDataFrame."""
        service = ProcessingService()

        gdf = gpd.GeoDataFrame(columns=["name", "geometry"], crs="EPSG:4326")
        result = service._standardize_crs(gdf)

        assert result.crs == TARGET_CRS
        assert len(result) == 0


class TestSpatialClipping:
    """Test cases for spatial clipping functionality."""

    def test_clip_to_boundary_success(self):
        """Test successful spatial clipping to district boundary."""
        service = ProcessingService()

        # Create boundary polygon
        boundary_geom = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
        boundary = gpd.GeoDataFrame({"name": ["District"]}, geometry=[boundary_geom], crs=TARGET_CRS)

        # Create points - some inside, some outside boundary
        points = [Point(2, 2), Point(7, 7), Point(3, 3)]  # 2 inside, 1 outside
        gdf = gpd.GeoDataFrame({"id": [1, 2, 3]}, geometry=points, crs=TARGET_CRS)

        result = service._clip_to_boundary(gdf, boundary)

        # Should keep only points inside boundary
        assert len(result) == 2
        assert result.crs == TARGET_CRS

    def test_clip_to_boundary_crs_mismatch(self):
        """Test clipping with CRS mismatch between datasets."""
        service = ProcessingService()

        # Create boundary in different CRS
        boundary_geom = Polygon([(13.4, 52.5), (13.5, 52.5), (13.5, 52.6), (13.4, 52.6)])
        boundary = gpd.GeoDataFrame({"name": ["District"]}, geometry=[boundary_geom], crs="EPSG:4326")

        # Create data in target CRS
        points = [Point(400000, 5820000)]  # Approximate Berlin coordinates in UTM
        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=points, crs=TARGET_CRS)

        result = service._clip_to_boundary(gdf, boundary)

        # Should handle CRS transformation
        assert result.crs == TARGET_CRS

    def test_clip_to_boundary_clipping_failure(self):
        """Test clipping fallback when clipping operation fails."""
        service = ProcessingService()

        boundary_geom = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
        boundary = gpd.GeoDataFrame({"name": ["District"]}, geometry=[boundary_geom], crs=TARGET_CRS)

        points = [Point(2, 2)]
        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=points, crs=TARGET_CRS)

        with (
            patch('geopandas.clip', side_effect=Exception("Clipping failed")),
            patch('app.services.processing_service.logger') as mock_logger,
        ):
                result = service._clip_to_boundary(gdf, boundary)

                # Should return original data on failure
                assert len(result) == 1
                mock_logger.warning.assert_called_once()

    def test_clip_to_boundary_empty_inputs(self):
        """Test clipping with empty GeoDataFrames."""
        service = ProcessingService()

        empty_gdf = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)
        boundary = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)

        result = service._clip_to_boundary(empty_gdf, boundary)
        assert len(result) == 0


class TestGeometryValidation:
    """Test cases for geometry validation and cleaning."""

    def test_validate_geometries_all_valid(self):
        """Test geometry validation with all valid geometries."""
        service = ProcessingService()

        valid_points = [Point(0, 0), Point(1, 1), Point(2, 2)]
        gdf = gpd.GeoDataFrame({"id": [1, 2, 3]}, geometry=valid_points, crs=TARGET_CRS)

        result = service._validate_geometries(gdf)

        assert len(result) == 3
        assert all(result.geometry.is_valid)

    def test_validate_geometries_invalid_geometries(self):
        """Test geometry validation and cleaning with invalid geometries."""
        service = ProcessingService()

        # Create invalid polygon (self-intersecting bowtie)
        invalid_polygon = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
        valid_point = Point(1, 1)

        gdf = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[invalid_polygon, valid_point],
            crs=TARGET_CRS
        )

        with patch('app.services.processing_service.logger') as mock_logger:
            result = service._validate_geometries(gdf)

            # Should clean invalid geometry
            assert len(result) == 2
            assert all(result.geometry.is_valid)
            mock_logger.warning.assert_called()

    def test_validate_geometries_cleaning_fails(self):
        """Test geometry validation when buffer(0) cleaning fails."""
        service = ProcessingService()

        # Create geometry that will remain invalid after buffer(0)
        invalid_geom = Point(0, 0)
        gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[invalid_geom], crs=TARGET_CRS)

        # Mock is_valid to return False even after cleaning
        with (
            patch.object(gdf.geometry, 'is_valid', side_effect=[
                pd.Series([False]),  # First check - invalid
                pd.Series([False])   # After buffer(0) - still invalid
            ]),
            patch('app.services.processing_service.logger') as mock_logger,
        ):
                result = service._validate_geometries(gdf)

                # Should remove uncleansable geometries
                assert len(result) == 0
                mock_logger.error.assert_called()

    def test_validate_geometries_empty_dataframe(self):
        """Test geometry validation with empty GeoDataFrame."""
        service = ProcessingService()

        empty_gdf = gpd.GeoDataFrame(columns=["id", "geometry"], crs=TARGET_CRS)
        result = service._validate_geometries(empty_gdf)

        assert len(result) == 0


class TestSchemaStandardization:
    """Test cases for schema standardization functionality."""

    def test_standardize_schema_complete_data(self):
        """Test schema standardization with complete dataset."""
        service = ProcessingService()

        geometry = [Point(0, 0), Point(1, 1)]
        gdf = gpd.GeoDataFrame(
            {
                "original_id": ["A", "B"],
                "name": ["Building A", "Building B"],
                "height": [10, 20]
            },
            geometry=geometry,
            crs=TARGET_CRS
        )

        result = service._standardize_schema(gdf, "gebaeude", "geoportal", "Pankow")

        # Validate standard schema columns
        for col in STANDARD_SCHEMA:
            assert col in result.columns

        # Validate data content
        assert all(result["dataset_type"] == "gebaeude")
        assert all(result["source_system"] == "geoportal")
        assert all(result["bezirk"] == "Pankow")
        assert result["feature_id"].tolist() == ["gebaeude_0", "gebaeude_1"]

        # Validate original attributes preservation
        assert len(result["original_attributes"]) == 2
        assert "original_id" in str(result["original_attributes"].iloc[0])
        assert "name" in str(result["original_attributes"].iloc[0])

    def test_standardize_schema_empty_dataframe(self):
        """Test schema standardization with empty GeoDataFrame."""
        service = ProcessingService()

        # Create empty GeoDataFrame with geometry column
        empty_gdf = gpd.GeoDataFrame(columns=["name"], geometry=gpd.GeoSeries([], crs=TARGET_CRS), crs=TARGET_CRS)
        result = service._standardize_schema(empty_gdf, "gebaeude", "geoportal", "Pankow")

        assert result.crs == TARGET_CRS
        assert len(result) == 0
        assert list(result.columns) == list(STANDARD_SCHEMA.keys())

    def test_standardize_schema_minimal_data(self):
        """Test schema standardization with minimal original data."""
        service = ProcessingService()

        geometry = [Point(0, 0)]
        gdf = gpd.GeoDataFrame({"geometry": geometry}, crs=TARGET_CRS)

        result = service._standardize_schema(gdf, "bezirksgrenzen", "geoportal", "Mitte")

        assert len(result) == 1
        assert result["dataset_type"].iloc[0] == "bezirksgrenzen"
        assert result["bezirk"].iloc[0] == "Mitte"
        assert result["feature_id"].iloc[0] == "bezirksgrenzen_0"
        assert result["original_attributes"].iloc[0] == {}  # No original attributes


class TestQualityAssurance:
    """Test cases for quality assurance statistics calculation."""

    def test_calculate_quality_stats_complete_data(self):
        """Test quality statistics calculation with complete harmonized data."""
        service = ProcessingService()

        # Create harmonized test data
        geometry = [Point(0, 0), Point(1, 1), Point(2, 2)]
        harmonized_gdf = gpd.GeoDataFrame(
            {
                "feature_id": ["district_0", "building_0", "stop_0"],
                "dataset_type": ["bezirksgrenzen", "gebaeude", "oepnv_haltestellen"],
                "source_system": ["geoportal", "geoportal", "osm"],
                "bezirk": ["Pankow", "Pankow", "Pankow"],
                "original_attributes": [{"name": "Pankow"}, {"height": 10}, {"name": "Station"}]
            },
            geometry=geometry,
            crs=TARGET_CRS
        )

        processing_stats = {"datasets_processed": 3, "datasets_failed": 0}

        result = service._calculate_quality_stats(harmonized_gdf, processing_stats)

        # Validate quality metrics
        assert result["total_features"] == 3
        assert result["geometry_validity_score"] == 1.0  # All valid geometries
        assert result["attribute_completeness_score"] == 1.0  # All required fields complete
        assert result["crs_consistency"] is True
        assert result["quality_score"] > 0.8  # Should be high quality
        assert "datasets_by_type" in result
        assert result["datasets_by_type"]["gebaeude"] == 1
        assert result["datasets_by_type"]["bezirksgrenzen"] == 1

    def test_calculate_quality_stats_empty_data(self):
        """Test quality statistics with empty harmonized data."""
        service = ProcessingService()

        empty_gdf = gpd.GeoDataFrame(columns=list(STANDARD_SCHEMA.keys()), crs=TARGET_CRS)
        processing_stats = {"datasets_processed": 0, "datasets_failed": 1}

        result = service._calculate_quality_stats(empty_gdf, processing_stats)

        assert result["total_features"] == 0
        assert result["geometry_validity_score"] == 0.0
        assert result["spatial_coverage_percentage"] == 0.0
        assert result["quality_score"] == 0.0
        assert result["datasets_by_type"] == {}

    def test_calculate_quality_stats_partial_quality(self):
        """Test quality statistics with mixed data quality."""
        service = ProcessingService()

        # Create data with missing values
        geometry = [Point(0, 0), Point(1, 1)]
        harmonized_gdf = gpd.GeoDataFrame(
            {
                "feature_id": ["building_0", "building_1"],
                "dataset_type": ["gebaeude", None],  # One missing dataset_type
                "source_system": ["geoportal", "geoportal"],
                "bezirk": ["Pankow", "Pankow"],
                "original_attributes": [{"height": 10}, {"height": 20}]
            },
            geometry=geometry,
            crs=TARGET_CRS
        )

        processing_stats = {"datasets_processed": 1, "datasets_failed": 1}

        result = service._calculate_quality_stats(harmonized_gdf, processing_stats)

        assert result["total_features"] == 2
        assert result["attribute_completeness_score"] < 1.0  # Some missing values
        assert 0.0 < result["quality_score"] < 1.0  # Partial quality


class TestIntegration:
    """Integration test cases for complete processing workflows."""

    @pytest.mark.asyncio
    async def test_end_to_end_processing_workflow(self):
        """Test complete end-to-end processing workflow with realistic data."""
        service = ProcessingService()

        # Create realistic Berlin district boundary
        district_polygon = Polygon([
            (13.4, 52.5), (13.5, 52.5), (13.5, 52.6), (13.4, 52.6)
        ])
        district_gdf = gpd.GeoDataFrame(
            {"bezirk_name": ["Pankow"], "bezirk_schluessel": ["03"]},
            geometry=[district_polygon],
            crs="EPSG:4326"  # Start in WGS84
        )

        # Create buildings data
        building_points = [Point(13.42, 52.52), Point(13.48, 52.58)]
        buildings_gdf = gpd.GeoDataFrame(
            {
                "nutzung": ["Wohnen", "Buero"],
                "geschosse": [4, 12],
                "baujahr": [1985, 2015]
            },
            geometry=building_points,
            crs="EPSG:4326"
        )

        # Create transport stops
        stop_points = [Point(13.43, 52.53)]
        transport_gdf = gpd.GeoDataFrame(
            {
                "name": ["S Pankow"],
                "operator": ["S-Bahn Berlin"],
                "transport_mode": ["light_rail"]
            },
            geometry=stop_points,
            crs="EPSG:4326"
        )

        # Create DataService-compatible input
        datasets = [
            {
                "dataset_id": "bezirksgrenzen_pankow",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "geodata": district_gdf,
                "predefined_metadata": {"name": "District Boundaries"},
                "runtime_stats": {"feature_count": 1}
            },
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": buildings_gdf,
                "predefined_metadata": {"name": "Buildings"},
                "runtime_stats": {"feature_count": 2}
            },
            {
                "dataset_id": "oepnv_haltestellen_pankow",
                "dataset_type": "oepnv_haltestellen",
                "source": "osm",
                "geodata": transport_gdf,
                "predefined_metadata": {"name": "Transport"},
                "runtime_stats": {"feature_count": 1}
            }
        ]

        # Execute harmonization
        result = await service.harmonize_datasets(datasets, "Pankow")

        # Validate complete workflow
        harmonized_data = result["harmonized_data"]

        # All data should be in target CRS
        assert harmonized_data.crs == TARGET_CRS

        # Should have all features with standard schema
        assert len(harmonized_data) == 4  # 1 district + 2 buildings + 1 transport
        assert all(col in harmonized_data.columns for col in STANDARD_SCHEMA)

        # All features should be within or related to district
        assert all(harmonized_data["bezirk"] == "Pankow")

        # Quality should be good
        assert result["quality_stats"]["quality_score"] > 0.7
        assert result["processing_stats"]["datasets_processed"] == 3
        assert result["processing_stats"]["datasets_failed"] == 0

    @pytest.mark.asyncio
    async def test_processing_error_propagation(self):
        """Test that processing errors are properly caught and propagated."""
        service = ProcessingService()

        # Create invalid input that will cause processing error
        invalid_datasets = [
            {
                "dataset_id": "invalid",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "geodata": "not_a_geodataframe",  # Invalid type
                "predefined_metadata": {},
                "runtime_stats": {}
            }
        ]

        with pytest.raises(ProcessingError):
            await service.harmonize_datasets(invalid_datasets, "Pankow")


class TestErrorHandling:
    """Test cases for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_extract_district_boundary_missing(self):
        """Test district boundary extraction when not present."""
        service = ProcessingService()

        datasets = [
            {
                "dataset_type": "gebaeude",
                "geodata": gpd.GeoDataFrame()
            }
        ]

        with pytest.raises(ValueError, match="District boundary dataset not found"):
            service._extract_district_boundary(datasets, "Pankow")

    def test_extract_district_boundary_empty(self):
        """Test district boundary extraction with empty boundary data."""
        service = ProcessingService()

        empty_boundary = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)
        datasets = [
            {
                "dataset_type": "bezirksgrenzen",
                "geodata": empty_boundary
            }
        ]

        with pytest.raises(ValueError, match="Empty district boundary"):
            service._extract_district_boundary(datasets, "Pankow")

    @pytest.mark.asyncio
    async def test_process_single_dataset_empty_input(self):
        """Test processing single dataset with empty geodata."""
        service = ProcessingService()

        boundary = gpd.GeoDataFrame(
            {"name": ["District"]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs=TARGET_CRS
        )

        dataset = {
            "dataset_type": "gebaeude",
            "source": "geoportal",
            "geodata": gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)  # Empty
        }

        result = await service._process_single_dataset(dataset, boundary, "Pankow")

        assert len(result) == 0
        assert result.crs == TARGET_CRS
        assert list(result.columns) == list(STANDARD_SCHEMA.keys())

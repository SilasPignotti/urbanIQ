"""
Comprehensive test suite for Export Service.

Tests ZIP package generation, geodata export, documentation creation,
and error handling scenarios for the Export Service.
"""

import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from app.models import Package
from app.services.export_service import (
    ExportError,
    ExportService,
    FileFormatError,
    PackageGenerationError,
)


class TestExportServiceInitialization:
    """Test Export Service initialization and setup."""

    def test_export_service_initialization(self):
        """Test Export Service initializes correctly."""
        with patch("app.services.export_service.settings") as mock_settings:
            mock_settings.export_dir = "/tmp/test_exports"

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                service = ExportService()

                assert service.export_dir == Path("/tmp/test_exports")
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_export_directory_creation(self):
        """Test export directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "exports"

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = str(export_dir)

                service = ExportService()

                assert export_dir.exists()
                assert service.export_dir == export_dir


class TestCreateGeodataPackage:
    """Test geodata package creation functionality."""

    @pytest.fixture
    def mock_datasets(self):
        """Create mock dataset dictionaries for testing."""
        # Create mock GeoDataFrames
        boundary_gdf = gpd.GeoDataFrame(
            {"name": ["Pankow"], "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]},
            crs="EPSG:25833",
        )

        buildings_gdf = gpd.GeoDataFrame(
            {
                "id": [1, 2],
                "type": ["residential", "commercial"],
                "geometry": [Point(0.3, 0.3), Point(0.7, 0.7)],
            },
            crs="EPSG:25833",
        )

        return [
            {
                "dataset_id": "bezirksgrenzen_pankow",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "geodata": boundary_gdf,
                "predefined_metadata": {
                    "name": "Bezirksgrenzen Berlin",
                    "license": "CC BY 3.0 DE",
                },
            },
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": buildings_gdf,
                "predefined_metadata": {
                    "name": "Gebäudedaten Berlin",
                    "license": "CC BY 3.0 DE",
                },
            },
        ]

    @pytest.fixture
    def mock_metadata_report(self):
        """Create mock metadata report for testing."""
        return """# Geodaten-Metadatenreport: Pankow

## Übersicht

- Erstellungsdatum: 2025-09-16
- Bezirk: Pankow
- Anzahl Datensätze: 2
- Koordinatensystem: ETRS89/UTM Zone 33N

## Datenqualität

Sehr hoch (0.95) - Vollständige Abdeckung des Bezirks.
"""

    def test_create_geodata_package_success(self, mock_datasets, mock_metadata_report):
        """Test successful geodata package creation."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("app.services.export_service.settings") as mock_settings,
        ):
            mock_settings.export_dir = temp_dir

            service = ExportService()

            package = service.create_geodata_package(
                datasets=mock_datasets,
                metadata_report=mock_metadata_report,
                bezirk="Pankow",
                job_id="test-job-123",
            )

            # Verify package creation
            assert isinstance(package, Package)
            assert package.job_id == "test-job-123"
            assert package.file_path.endswith(".zip")
            assert package.file_size > 0
            assert package.metadata_report == mock_metadata_report

            # Verify ZIP file exists
            zip_path = Path(package.file_path)
            assert zip_path.exists()
            assert zip_path.suffix == ".zip"

    def test_create_geodata_package_with_empty_datasets(self, mock_metadata_report):
        """Test package creation with empty datasets list."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("app.services.export_service.settings") as mock_settings,
        ):
            mock_settings.export_dir = temp_dir

            service = ExportService()

            package = service.create_geodata_package(
                datasets=[],
                metadata_report=mock_metadata_report,
                bezirk="Pankow",
                job_id="test-job-empty",
            )

            # Should still create package with documentation only
            assert isinstance(package, Package)
            assert package.file_size > 0

            # Verify ZIP contains documentation files
            with zipfile.ZipFile(package.file_path, "r") as zip_file:
                file_list = zip_file.namelist()
                assert "README.md" in file_list
                assert "METADATA.md" in file_list

    def test_package_filename_generation(self, mock_datasets, mock_metadata_report):
        """Test package filename includes district and timestamp."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("app.services.export_service.settings") as mock_settings,
        ):
            mock_settings.export_dir = temp_dir

            service = ExportService()

            with patch("app.services.export_service.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value.strftime.return_value = "20250916_143000"

                package = service.create_geodata_package(
                    datasets=mock_datasets,
                    metadata_report=mock_metadata_report,
                    bezirk="Charlottenburg-Wilmersdorf",
                    job_id="test-job-filename",
                )

                filename = Path(package.file_path).name
                assert "charlottenburg-wilmersdorf" in filename.lower()
                assert "20250916_143000" in filename
                assert filename.endswith(".zip")


class TestGeodataExport:
    """Test geodata file export functionality."""

    @pytest.fixture
    def sample_geodataframe(self):
        """Create sample GeoDataFrame for testing."""
        return gpd.GeoDataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Feature A", "Feature B", "Feature C"],
                "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
            },
            crs="EPSG:25833",
        )

    def test_export_geodata_files(self, sample_geodataframe):
        """Test geodata export in multiple formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()

                datasets = [
                    {
                        "dataset_type": "test_data",
                        "geodata": sample_geodataframe,
                    }
                ]

                service._export_geodata_files(datasets, temp_path, mock_logger)

                # Verify GeoJSON export
                geojson_file = temp_path / "test_data.geojson"
                assert geojson_file.exists()

                # Verify Shapefile export (multiple files)
                shp_files = list(temp_path.glob("test_data.*"))
                assert len(shp_files) >= 3  # .shp, .shx, .dbf minimum
                assert any(f.suffix == ".shp" for f in shp_files)

    def test_export_geodata_format_geojson(self, sample_geodataframe):
        """Test specific GeoJSON format export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()

                service._export_geodata_format(
                    sample_geodataframe, "buildings", "geojson", temp_path, mock_logger
                )

                output_file = temp_path / "buildings.geojson"
                assert output_file.exists()

                # Verify file can be read back
                reloaded_gdf = gpd.read_file(output_file)
                assert len(reloaded_gdf) == 3
                assert list(reloaded_gdf.columns) == ["id", "name", "geometry"]

    def test_export_geodata_format_shapefile(self, sample_geodataframe):
        """Test specific Shapefile format export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()

                service._export_geodata_format(
                    sample_geodataframe, "districts", "shapefile", temp_path, mock_logger
                )

                shp_file = temp_path / "districts.shp"
                assert shp_file.exists()

                # Verify shapefile can be read back
                reloaded_gdf = gpd.read_file(shp_file)
                assert len(reloaded_gdf) == 3

    def test_export_empty_geodataframe(self):
        """Test handling of empty GeoDataFrame."""
        empty_gdf = gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:25833")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()

                datasets = [
                    {
                        "dataset_type": "empty_data",
                        "geodata": empty_gdf,
                    }
                ]

                # Should handle empty datasets gracefully
                service._export_geodata_files(datasets, temp_path, mock_logger)

                # Check warning was logged
                mock_logger.warning.assert_called_with(
                    "Skipping empty dataset", dataset_type="empty_data"
                )

    def test_export_geodata_format_error(self, sample_geodataframe):
        """Test geodata export format error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()

                # Mock to_file to raise an exception
                with (
                    patch.object(
                        sample_geodataframe, "to_file", side_effect=Exception("Export failed")
                    ),
                    pytest.raises(FileFormatError, match="Failed to export test_data as geojson"),
                ):
                    service._export_geodata_format(
                        sample_geodataframe, "test_data", "geojson", temp_path, mock_logger
                    )


class TestDocumentationCreation:
    """Test documentation file creation."""

    @pytest.fixture
    def sample_datasets(self):
        """Sample datasets for documentation testing."""
        return [
            {
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "predefined_metadata": {"name": "District Boundaries"},
            },
            {
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "predefined_metadata": {"name": "Building Data"},
            },
            {
                "dataset_type": "oepnv_haltestellen",
                "source": "osm",
                "predefined_metadata": {"name": "Transport Stops"},
            },
        ]

    def test_create_documentation_files(self, sample_datasets):
        """Test creation of all documentation files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()
                metadata_report = "# Test Metadata Report"

                service._create_documentation_files(
                    sample_datasets, metadata_report, "Pankow", temp_path, mock_logger
                )

                # Verify all documentation files created
                assert (temp_path / "README.md").exists()
                assert (temp_path / "METADATA.md").exists()
                assert (temp_path / "LICENSE_GEOPORTAL.txt").exists()
                assert (temp_path / "LICENSE_OSM.txt").exists()

                # Verify METADATA.md content
                metadata_content = (temp_path / "METADATA.md").read_text()
                assert metadata_content == metadata_report

    def test_generate_readme_content(self, sample_datasets):
        """Test README.md content generation."""
        with patch("app.services.export_service.settings") as mock_settings:
            mock_settings.export_dir = "/tmp/test"

            service = ExportService()

            with patch("app.services.export_service.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value.strftime.return_value = "2025-09-16 14:30 UTC"

                readme_content = service._generate_readme_content(sample_datasets, "Pankow")

                # Verify README content structure
                assert "# Geodatenpaket Pankow" in readme_content
                assert "2025-09-16 14:30 UTC" in readme_content
                assert "ETRS89/UTM Zone 33N (EPSG:25833)" in readme_content
                assert "Anzahl Datensätze: 3" in readme_content

                # Verify dataset sections
                assert "## Enthaltene Dateien" in readme_content
                assert "### Bezirksgrenzen Berlin" in readme_content
                assert "### Gebäudedaten Berlin" in readme_content
                assert "### ÖPNV-Haltestellen" in readme_content

                # Verify file format mentions
                assert ".geojson" in readme_content
                assert ".shp" in readme_content

    def test_get_dataset_display_name(self):
        """Test dataset display name mapping."""
        with patch("app.services.export_service.settings") as mock_settings:
            mock_settings.export_dir = "/tmp/test"

            service = ExportService()

            assert service._get_dataset_display_name("bezirksgrenzen") == "Bezirksgrenzen Berlin"
            assert service._get_dataset_display_name("gebaeude") == "Gebäudedaten Berlin"
            assert service._get_dataset_display_name("oepnv_haltestellen") == "ÖPNV-Haltestellen"
            assert service._get_dataset_display_name("unknown_type") == "Unknown_Type"

    def test_create_license_files(self, sample_datasets):
        """Test license file creation for different sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = "/tmp/test"

                service = ExportService()
                mock_logger = MagicMock()

                service._create_license_files(sample_datasets, temp_path, mock_logger)

                # Verify license files created
                geoportal_license = temp_path / "LICENSE_GEOPORTAL.txt"
                osm_license = temp_path / "LICENSE_OSM.txt"

                assert geoportal_license.exists()
                assert osm_license.exists()

                # Verify license content
                geoportal_content = geoportal_license.read_text()
                assert "CC BY 3.0 DE" in geoportal_content
                assert "Berlin Geoportal" in geoportal_content

                osm_content = osm_license.read_text()
                assert "Open Database License (ODbL)" in osm_content
                assert "OpenStreetMap Contributors" in osm_content


class TestZipPackageCreation:
    """Test ZIP package creation functionality."""

    def test_create_zip_package(self):
        """Test ZIP file creation from directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source"
            source_path.mkdir()

            # Create test files
            (source_path / "test1.txt").write_text("Content 1")
            (source_path / "test2.geojson").write_text('{"type": "FeatureCollection"}')

            # Create subdirectory with file
            sub_dir = source_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "test3.md").write_text("# Test")

            output_zip = Path(temp_dir) / "test_package.zip"

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = temp_dir

                service = ExportService()
                mock_logger = MagicMock()

                service._create_zip_package(source_path, output_zip, mock_logger)

                # Verify ZIP file created
                assert output_zip.exists()

                # Verify ZIP contents
                with zipfile.ZipFile(output_zip, "r") as zip_file:
                    file_list = zip_file.namelist()
                    assert "test1.txt" in file_list
                    assert "test2.geojson" in file_list
                    assert "subdir/test3.md" in file_list

                    # Verify file contents
                    assert zip_file.read("test1.txt").decode() == "Content 1"

    def test_create_zip_package_error(self):
        """Test ZIP creation error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source"
            source_path.mkdir()

            # Invalid output path (directory that doesn't exist)
            output_zip = Path(temp_dir) / "nonexistent" / "test.zip"

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = temp_dir

                service = ExportService()
                mock_logger = MagicMock()

                with pytest.raises(PackageGenerationError, match="Failed to create ZIP file"):
                    service._create_zip_package(source_path, output_zip, mock_logger)


class TestPackageCleanup:
    """Test package cleanup functionality."""

    def test_cleanup_expired_packages(self):
        """Test cleanup of expired package files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)

            # Create old ZIP file (simulate expired - 48 hours old)
            old_zip = export_dir / "old_package.zip"
            old_zip.write_text("old content")
            # Use os.utime to set file modification time
            import os

            old_time = (datetime.now() - timedelta(hours=48)).timestamp()
            os.utime(old_zip, (old_time, old_time))

            # Create new ZIP file (not expired)
            new_zip = export_dir / "new_package.zip"
            new_zip.write_text("new content")

            # Create non-ZIP file (should be ignored)
            other_file = export_dir / "other.txt"
            other_file.write_text("other content")
            other_time = (datetime.now() - timedelta(hours=48)).timestamp()
            os.utime(other_file, (other_time, other_time))

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = str(export_dir)

                service = ExportService()

                cleaned_count = service.cleanup_expired_packages()

                # Verify cleanup results
                assert cleaned_count == 1
                assert not old_zip.exists()  # Old ZIP removed
                assert new_zip.exists()  # New ZIP kept
                assert other_file.exists()  # Non-ZIP ignored

    def test_cleanup_no_expired_packages(self):
        """Test cleanup when no packages are expired."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)

            # Create recent ZIP file
            recent_zip = export_dir / "recent_package.zip"
            recent_zip.write_text("recent content")

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = str(export_dir)

                service = ExportService()

                cleaned_count = service.cleanup_expired_packages()

                # Verify no cleanup occurred
                assert cleaned_count == 0
                assert recent_zip.exists()

    def test_cleanup_error_handling(self):
        """Test cleanup error handling for individual files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)

            # Create old ZIP file
            old_zip = export_dir / "old_package.zip"
            old_zip.write_text("content")
            import os

            old_time = (datetime.now() - timedelta(hours=48)).timestamp()
            os.utime(old_zip, (old_time, old_time))

            with patch("app.services.export_service.settings") as mock_settings:
                mock_settings.export_dir = str(export_dir)

                service = ExportService()

                # Mock unlink to raise exception
                with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
                    # Should handle individual file errors gracefully
                    cleaned_count = service.cleanup_expired_packages()

                    # Should return 0 due to error
                    assert cleaned_count == 0

    def test_cleanup_directory_error(self):
        """Test cleanup when directory operations fail."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("app.services.export_service.settings") as mock_settings,
        ):
            mock_settings.export_dir = str(temp_dir)

            service = ExportService()

            # Mock glob to raise exception
            with (
                patch.object(Path, "glob", side_effect=OSError("Directory access failed")),
                pytest.raises(ExportError, match="Cleanup operation failed"),
            ):
                service.cleanup_expired_packages()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_package_generation_error_handling(self, mock_datasets=None):
        """Test PackageGenerationError in main method."""
        if mock_datasets is None:
            mock_datasets = []
        with patch("app.services.export_service.settings") as mock_settings:
            mock_settings.export_dir = "/tmp/test"

            service = ExportService()

            # Mock _export_geodata_files to raise exception
            with (
                patch.object(
                    service, "_export_geodata_files", side_effect=Exception("Export failed")
                ),
                pytest.raises(PackageGenerationError, match="Failed to create package"),
            ):
                service.create_geodata_package(
                    datasets=[],
                    metadata_report="Test report",
                    bezirk="Pankow",
                    job_id="test-job",
                )

    def test_file_format_error_inheritance(self):
        """Test FileFormatError inherits from ExportError."""
        error = FileFormatError("Test error")
        assert isinstance(error, ExportError)
        assert isinstance(error, Exception)

    def test_package_generation_error_inheritance(self):
        """Test PackageGenerationError inherits from ExportError."""
        error = PackageGenerationError("Test error")
        assert isinstance(error, ExportError)
        assert isinstance(error, Exception)


class TestExportServiceIntegration:
    """Integration tests for Export Service with real file operations."""

    @pytest.mark.integration
    def test_full_package_creation_workflow(self):
        """Test complete package creation workflow."""
        # Create realistic test datasets
        boundary_gdf = gpd.GeoDataFrame(
            {
                "bezirk_name": ["Pankow"],
                "flaeche_ha": [10325],
                "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
            },
            crs="EPSG:25833",
        )

        buildings_gdf = gpd.GeoDataFrame(
            {
                "nutzung": ["Wohnen", "Gewerbe"],
                "geschosse": [3, 5],
                "geometry": [Point(3, 3), Point(7, 7)],
            },
            crs="EPSG:25833",
        )

        datasets = [
            {
                "dataset_id": "bezirksgrenzen_pankow",
                "dataset_type": "bezirksgrenzen",
                "source": "geoportal",
                "geodata": boundary_gdf,
            },
            {
                "dataset_id": "gebaeude_pankow",
                "dataset_type": "gebaeude",
                "source": "geoportal",
                "geodata": buildings_gdf,
            },
        ]

        metadata_report = """# Geodaten-Metadatenreport: Pankow

## Übersicht
- Bezirk: Pankow
- Datensätze: 2
- Qualität: Sehr hoch

## Details
Vollständige Geodaten für den Bezirk Pankow.
"""

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("app.services.export_service.settings") as mock_settings,
        ):
            mock_settings.export_dir = temp_dir

            service = ExportService()

            package = service.create_geodata_package(
                datasets=datasets,
                metadata_report=metadata_report,
                bezirk="Pankow",
                job_id="integration-test-job",
            )

            # Comprehensive validation
            assert isinstance(package, Package)
            assert package.job_id == "integration-test-job"
            assert Path(package.file_path).exists()
            assert package.file_size > 1000  # Should be substantial

            # Validate ZIP contents
            with zipfile.ZipFile(package.file_path, "r") as zip_file:
                file_list = zip_file.namelist()

                # Check for geodata files
                assert "bezirksgrenzen.geojson" in file_list
                assert "bezirksgrenzen.shp" in file_list
                assert "gebaeude.geojson" in file_list
                assert "gebaeude.shp" in file_list

                # Check for documentation
                assert "README.md" in file_list
                assert "METADATA.md" in file_list
                assert "LICENSE_GEOPORTAL.txt" in file_list

                # Validate metadata content
                metadata_content = zip_file.read("METADATA.md").decode()
                assert "Pankow" in metadata_content

                # Validate README content
                readme_content = zip_file.read("README.md").decode()
                assert "Geodatenpaket Pankow" in readme_content
                assert "EPSG:25833" in readme_content

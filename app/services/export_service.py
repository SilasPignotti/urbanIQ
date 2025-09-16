"""
Export Service for creating downloadable ZIP packages with geodata and metadata.

Generates professional ZIP packages containing harmonized geodata in multiple formats,
LLM-generated metadata reports, and comprehensive documentation.
"""

import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import structlog

from app.config import settings
from app.models import Package

logger = structlog.get_logger("urbaniq.export_service")

# Supported geodata export formats
EXPORT_FORMATS = {
    "geojson": {
        "extension": ".geojson",
        "driver": "GeoJSON",
        "description": "GeoJSON format for web applications and QGIS",
    },
    "shapefile": {
        "extension": ".shp",
        "driver": "ESRI Shapefile",
        "description": "Shapefile format for ArcGIS and traditional GIS software",
    },
}

# License information for different data sources
LICENSE_TEMPLATES = {
    "geoportal": """# Lizenzinformationen - Berlin Geoportal

## Datenlizenz Deutschland - Zero - Version 2.0

Quelle: Berlin Geoportal (https://gdi.berlin.de)
Lizenz: CC BY 3.0 DE (https://creativecommons.org/licenses/by/3.0/de/)

### Nutzungsbedingungen:
- Freie Nutzung für kommerzielle und nicht-kommerzielle Zwecke
- Quellenangabe erforderlich: "Datenquelle: Berlin Geoportal"
- Keine Haftung für Vollständigkeit oder Aktualität der Daten
""",
    "osm": """# Lizenzinformationen - OpenStreetMap

## Open Database License (ODbL)

Quelle: OpenStreetMap Contributors (https://www.openstreetmap.org)
Lizenz: ODbL (https://opendatacommons.org/licenses/odbl/)

### Nutzungsbedingungen:
- Freie Nutzung mit Share-Alike Lizenz
- Quellenangabe erforderlich: "© OpenStreetMap Contributors"
- Abgeleitete Werke müssen unter gleicher Lizenz stehen
- Weitere Details: https://www.openstreetmap.org/copyright
""",
}


class ExportError(Exception):
    """Base exception for export service errors."""

    pass


class PackageGenerationError(ExportError):
    """Raised when ZIP package generation fails."""

    pass


class FileFormatError(ExportError):
    """Raised when geodata format conversion fails."""

    pass


class ExportService:
    """
    Service for creating downloadable ZIP packages with geodata and metadata.

    Generates professional packages containing harmonized geodata in multiple formats,
    comprehensive metadata reports, and licensing documentation.
    """

    def __init__(self) -> None:
        """Initialize Export Service with configured export directory."""
        logger.info("Initializing Export Service")

        # Ensure export directory exists
        self.export_dir = Path(settings.export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Export Service initialized", export_dir=str(self.export_dir))

    def create_geodata_package(
        self,
        datasets: list[dict[str, Any]],
        metadata_report: str,
        bezirk: str,
        job_id: str,
    ) -> Package:
        """
        Create ZIP package with geodata files and metadata reports.

        Args:
            datasets: List of dataset dictionaries from ProcessingService
            metadata_report: LLM-generated metadata report from MetadataService
            bezirk: Target district name for package naming
            job_id: Originating job ID for package association

        Returns:
            Package model instance with file path and metadata

        Raises:
            PackageGenerationError: If ZIP creation fails
            FileFormatError: If geodata format conversion fails
        """
        export_logger = logger.bind(bezirk=bezirk, job_id=job_id)
        export_logger.info("Starting geodata package creation", dataset_count=len(datasets))

        try:
            # Generate unique package filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            package_filename = f"geodata_{bezirk.lower()}_{timestamp}.zip"
            package_path = self.export_dir / package_filename

            # Create ZIP package
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Export geodata in multiple formats
                self._export_geodata_files(datasets, temp_path, export_logger)

                # Create documentation files
                self._create_documentation_files(
                    datasets, metadata_report, bezirk, temp_path, export_logger
                )

                # Create ZIP package
                self._create_zip_package(temp_path, package_path, export_logger)

            # Calculate file size
            file_size = package_path.stat().st_size

            # Create Package model instance
            package = Package(
                job_id=job_id,
                file_path=str(package_path.absolute()),
                file_size=file_size,
                metadata_report=metadata_report,
            )

            export_logger.info(
                "Package creation completed",
                package_id=package.id,
                file_size_mb=package.get_file_size_mb(),
                file_path=str(package_path),
            )

            return package

        except Exception as e:
            export_logger.error("Package creation failed", error=str(e))
            raise PackageGenerationError(f"Failed to create package: {str(e)}") from e

    def _export_geodata_files(
        self, datasets: list[dict[str, Any]], output_dir: Path, logger_instance: Any
    ) -> None:
        """Export geodata in multiple formats (GeoJSON, Shapefile)."""
        logger_instance.info("Exporting geodata files")

        for dataset in datasets:
            dataset_type = dataset.get("dataset_type", "unknown")
            geodata = dataset.get("geodata")

            if geodata is None or geodata.empty:
                logger_instance.warning(
                    "Skipping empty dataset", dataset_type=dataset_type
                )
                continue

            # Export in GeoJSON format (primary)
            self._export_geodata_format(
                geodata, dataset_type, "geojson", output_dir, logger_instance
            )

            # Export in Shapefile format (compatibility)
            self._export_geodata_format(
                geodata, dataset_type, "shapefile", output_dir, logger_instance
            )

    def _export_geodata_format(
        self,
        geodata: gpd.GeoDataFrame,
        dataset_type: str,
        format_name: str,
        output_dir: Path,
        logger_instance: Any,
    ) -> None:
        """Export geodata in specified format."""
        try:
            format_config = EXPORT_FORMATS[format_name]
            filename = f"{dataset_type}{format_config['extension']}"
            output_path = output_dir / filename

            # Export using GeoPandas
            geodata.to_file(
                output_path,
                driver=format_config["driver"],
                encoding="utf-8",
            )

            logger_instance.info(
                "Geodata exported",
                dataset_type=dataset_type,
                format=format_name,
                features=len(geodata),
                file=filename,
            )

        except Exception as e:
            logger_instance.error(
                "Geodata export failed",
                dataset_type=dataset_type,
                format=format_name,
                error=str(e),
            )
            raise FileFormatError(
                f"Failed to export {dataset_type} as {format_name}: {str(e)}"
            ) from e

    def _create_documentation_files(
        self,
        datasets: list[dict[str, Any]],
        metadata_report: str,
        bezirk: str,
        output_dir: Path,
        logger_instance: Any,
    ) -> None:
        """Create documentation files (README, metadata, licenses)."""
        logger_instance.info("Creating documentation files")

        # Create README.md with usage instructions
        readme_content = self._generate_readme_content(datasets, bezirk)
        (output_dir / "README.md").write_text(readme_content, encoding="utf-8")

        # Save metadata report
        (output_dir / "METADATA.md").write_text(metadata_report, encoding="utf-8")

        # Create license files based on data sources
        self._create_license_files(datasets, output_dir, logger_instance)

        logger_instance.info("Documentation files created")

    def _generate_readme_content(self, datasets: list[dict[str, Any]], bezirk: str) -> str:
        """Generate README.md content with usage instructions."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        readme_lines = [
            f"# Geodatenpaket {bezirk}",
            "",
            f"Erstellt am: {timestamp}",
            "Koordinatensystem: ETRS89/UTM Zone 33N (EPSG:25833)",
            f"Anzahl Datensätze: {len(datasets)}",
            "",
            "## Enthaltene Dateien",
            "",
        ]

        # List geodata files
        for dataset in datasets:
            dataset_type = dataset.get("dataset_type", "unknown")
            dataset_name = self._get_dataset_display_name(dataset_type)

            readme_lines.extend([
                f"### {dataset_name}",
                f"- `{dataset_type}.geojson` - GeoJSON Format für Web-Anwendungen",
                f"- `{dataset_type}.shp` + Begleitdateien - Shapefile für GIS-Software",
                "",
            ])

        readme_lines.extend([
            "## Dokumentation",
            "",
            "- `METADATA.md` - Detaillierte Metadaten und Qualitätsbewertung",
            "- `LICENSE_*.txt` - Lizenzinformationen für Datenquellen",
            "",
            "## Koordinatensystem",
            "",
            "Alle Geodaten sind im Koordinatensystem ETRS89/UTM Zone 33N (EPSG:25833) projiziert.",
            "Für die Verwendung in Web-Anwendungen kann eine Transformation nach WGS84 (EPSG:4326) erforderlich sein.",
            "",
            "## Empfohlene GIS-Software",
            "",
            "- **QGIS** (kostenlos): Unterstützt GeoJSON und Shapefile direkt",
            "- **ArcGIS**: Verwenden Sie die Shapefile-Dateien",
            "- **Web-Anwendungen**: Verwenden Sie die GeoJSON-Dateien",
            "",
            "## Support",
            "",
            "Bei Fragen zur Datennutzung konsultieren Sie die METADATA.md Datei.",
        ])

        return "\n".join(readme_lines)

    def _get_dataset_display_name(self, dataset_type: str) -> str:
        """Get human-readable display name for dataset type."""
        display_names = {
            "bezirksgrenzen": "Bezirksgrenzen Berlin",
            "gebaeude": "Gebäudedaten Berlin",
            "oepnv_haltestellen": "ÖPNV-Haltestellen",
        }
        return display_names.get(dataset_type, dataset_type.title())

    def _create_license_files(
        self, datasets: list[dict[str, Any]], output_dir: Path, logger_instance: Any
    ) -> None:
        """Create license files based on data sources."""
        sources_found = set()

        for dataset in datasets:
            source = dataset.get("source", "unknown")
            if source in LICENSE_TEMPLATES:
                sources_found.add(source)

        for source in sources_found:
            license_filename = f"LICENSE_{source.upper()}.txt"
            license_path = output_dir / license_filename
            license_content = LICENSE_TEMPLATES[source]

            license_path.write_text(license_content, encoding="utf-8")
            logger_instance.info("License file created", source=source, file=license_filename)

    def _create_zip_package(
        self, source_dir: Path, output_path: Path, logger_instance: Any
    ) -> None:
        """Create ZIP package from temporary directory."""
        logger_instance.info("Creating ZIP package", output_path=str(output_path))

        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        # Calculate relative path for ZIP archive
                        arcname = file_path.relative_to(source_dir)
                        zip_file.write(file_path, arcname)

            logger_instance.info("ZIP package created successfully")

        except Exception as e:
            logger_instance.error("ZIP creation failed", error=str(e))
            raise PackageGenerationError(f"Failed to create ZIP file: {str(e)}") from e

    def cleanup_expired_packages(self) -> int:
        """
        Clean up expired packages from filesystem.

        Returns:
            Number of packages cleaned up

        Raises:
            ExportError: If cleanup operation fails
        """
        logger.info("Starting package cleanup")
        cleaned_count = 0

        try:
            # Find all ZIP files in export directory
            zip_files = list(self.export_dir.glob("*.zip"))

            for zip_file in zip_files:
                try:
                    # Check if file is older than 24 hours (package expiration default)
                    file_age_hours = (datetime.utcnow().timestamp() - zip_file.stat().st_mtime) / 3600

                    if file_age_hours > 24:
                        zip_file.unlink()
                        cleaned_count += 1
                        logger.info("Expired package cleaned", file=zip_file.name, age_hours=file_age_hours)

                except Exception as e:
                    logger.warning("Failed to clean package", file=zip_file.name, error=str(e))

            logger.info("Package cleanup completed", cleaned_count=cleaned_count)
            return cleaned_count

        except Exception as e:
            logger.error("Package cleanup failed", error=str(e))
            raise ExportError(f"Cleanup operation failed: {str(e)}") from e

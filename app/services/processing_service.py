"""
Processing Service for geodata harmonization and standardization.

Harmonizes geodata from multiple sources (Berlin Geoportal WFS, OpenStreetMap) by standardizing
CRS to EPSG:25833, clipping to district boundaries, applying unified schema, validating geometries,
and generating quality assurance statistics.
"""

import logging
from datetime import datetime
from typing import Any

import geopandas as gpd
import pandas as pd

logger = logging.getLogger("urbaniq.processing_service")

# Standard CRS for Berlin geodata
TARGET_CRS = "EPSG:25833"

# Standard schema field mapping
STANDARD_SCHEMA = {
    "feature_id": "str",
    "dataset_type": "str",
    "source_system": "str",
    "bezirk": "str",
    "geometry": "geometry",
    "original_attributes": "object",
}


class ProcessingService:
    """
    Service for harmonizing geodata from multiple sources into standardized format.

    Processes DataService output by standardizing CRS, clipping to boundaries,
    applying unified schema, validating geometries, and calculating quality metrics.
    """

    def __init__(self) -> None:
        """Initialize Processing Service."""
        logger.info("Initializing Processing Service")

    async def harmonize_datasets(
        self, datasets: list[dict[str, Any]], target_district: str
    ) -> dict[str, Any]:
        """
        Harmonize multiple geodatasets into unified format.

        Processes DataService output by standardizing CRS to EPSG:25833, clipping all
        datasets to district boundary, applying unified schema while preserving original
        attributes, validating geometries, and calculating comprehensive quality statistics.

        Args:
            datasets: List of dataset dictionaries from DataService.fetch_datasets_for_request()
            target_district: Berlin district name for spatial context and validation

        Returns:
            Dictionary containing harmonized GeoDataFrame and processing statistics

        Raises:
            ValueError: If no datasets provided or missing required district boundary
            ProcessingError: If critical processing steps fail
        """
        if not datasets:
            raise ValueError("No datasets provided for harmonization")

        logger.info(
            f"Starting harmonization for {len(datasets)} datasets in {target_district}",
            extra={"target_district": target_district, "dataset_count": len(datasets)},
        )

        start_time = datetime.now()

        try:
            # Extract district boundary (always first dataset from DataService)
            district_boundary = self._extract_district_boundary(datasets, target_district)

            # Process all datasets through harmonization pipeline
            harmonized_datasets = []
            processing_stats = {"datasets_processed": 0, "datasets_failed": 0, "total_features": 0}

            for dataset in datasets:
                try:
                    processed_dataset = await self._process_single_dataset(
                        dataset, district_boundary, target_district
                    )
                    harmonized_datasets.append(processed_dataset)
                    processing_stats["datasets_processed"] += 1
                    processing_stats["total_features"] += len(processed_dataset)

                except Exception as e:
                    logger.error(
                        f"Failed to process dataset {dataset.get('dataset_type', 'unknown')}: {str(e)}",
                        extra={"dataset_id": dataset.get("dataset_id"), "error": str(e)},
                    )
                    processing_stats["datasets_failed"] += 1

            # Combine all harmonized datasets
            if harmonized_datasets:
                harmonized_gdf = pd.concat(harmonized_datasets, ignore_index=True)
                harmonized_gdf = gpd.GeoDataFrame(harmonized_gdf, crs=TARGET_CRS)
            else:
                harmonized_gdf = gpd.GeoDataFrame(
                    columns=list(STANDARD_SCHEMA.keys()), crs=TARGET_CRS
                )

            # Calculate final quality statistics
            quality_stats = self._calculate_quality_stats(harmonized_gdf, processing_stats)

            processing_duration = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"Harmonization completed in {processing_duration:.0f}ms. "
                f"Processed {processing_stats['datasets_processed']} datasets, "
                f"{processing_stats['total_features']} total features",
                extra={
                    "processing_duration_ms": processing_duration,
                    "datasets_processed": processing_stats["datasets_processed"],
                    "datasets_failed": processing_stats["datasets_failed"],
                    "total_features": processing_stats["total_features"],
                },
            )

            return {
                "harmonized_data": harmonized_gdf,
                "processing_stats": processing_stats,
                "quality_stats": quality_stats,
                "processing_duration_ms": processing_duration,
                "target_district": target_district,
                "total_datasets": len(datasets),
                "successful_datasets": processing_stats["datasets_processed"],
            }

        except Exception as e:
            processing_duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"Harmonization failed after {processing_duration:.0f}ms: {str(e)}",
                extra={"target_district": target_district, "error": str(e)},
            )
            raise ProcessingError(
                f"Failed to harmonize datasets for {target_district}: {str(e)}"
            ) from e

    def _extract_district_boundary(
        self, datasets: list[dict[str, Any]], target_district: str
    ) -> gpd.GeoDataFrame:
        """
        Extract district boundary from datasets for spatial filtering.

        Args:
            datasets: List of dataset dictionaries from DataService
            target_district: Expected district name for validation

        Returns:
            GeoDataFrame with district boundary geometry in EPSG:25833

        Raises:
            ValueError: If district boundary not found or invalid
        """
        district_dataset = None
        for dataset in datasets:
            if dataset.get("dataset_type") == "bezirksgrenzen":
                district_dataset = dataset
                break

        if not district_dataset:
            raise ValueError("District boundary dataset not found in input datasets")

        district_gdf = district_dataset["geodata"]
        if district_gdf.empty:
            raise ValueError(f"Empty district boundary for {target_district}")

        # Ensure correct CRS
        district_gdf = self._standardize_crs(district_gdf)

        logger.debug(
            f"Extracted district boundary for {target_district}: {len(district_gdf)} features",
            extra={"district": target_district, "boundary_features": len(district_gdf)},
        )

        return district_gdf

    async def _process_single_dataset(
        self, dataset: dict[str, Any], district_boundary: gpd.GeoDataFrame, target_district: str
    ) -> gpd.GeoDataFrame:
        """
        Process single dataset through complete harmonization pipeline.

        Args:
            dataset: Single dataset dictionary from DataService
            district_boundary: District boundary for spatial clipping
            target_district: District name for schema standardization

        Returns:
            Harmonized GeoDataFrame with standardized schema and geometry
        """
        dataset_type = dataset.get("dataset_type", "unknown")
        source_system = dataset.get("source", "unknown")

        logger.debug(f"Processing dataset: {dataset_type} from {source_system}")

        # Extract and validate GeoDataFrame
        gdf = dataset["geodata"]
        if gdf.empty:
            logger.warning(f"Empty dataset: {dataset_type}")
            return gpd.GeoDataFrame(columns=list(STANDARD_SCHEMA.keys()), crs=TARGET_CRS)

        # Step 1: Standardize CRS
        gdf = self._standardize_crs(gdf)

        # Step 2: Clip to district boundary (except for district boundary itself)
        if dataset_type != "bezirksgrenzen":
            gdf = self._clip_to_boundary(gdf, district_boundary)

        # Step 3: Validate and clean geometries
        gdf = self._validate_geometries(gdf)

        # Step 4: Apply standard schema
        gdf = self._standardize_schema(gdf, dataset_type, source_system, target_district)

        return gdf

    def _standardize_crs(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Standardize coordinate reference system to EPSG:25833.

        Args:
            gdf: Input GeoDataFrame with any CRS

        Returns:
            GeoDataFrame transformed to EPSG:25833
        """
        if gdf.empty:
            return gpd.GeoDataFrame(columns=gdf.columns, crs=TARGET_CRS)

        # Handle missing CRS
        if gdf.crs is None:
            logger.warning("GeoDataFrame has no CRS, assuming EPSG:25833")
            gdf.set_crs(TARGET_CRS, inplace=True)
        elif gdf.crs != TARGET_CRS:
            logger.debug(f"Transforming CRS from {gdf.crs} to {TARGET_CRS}")
            gdf = gdf.to_crs(TARGET_CRS)

        return gdf

    def _clip_to_boundary(
        self, gdf: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Clip GeoDataFrame to district boundary for consistent spatial extent.

        Args:
            gdf: GeoDataFrame to clip
            boundary: District boundary for clipping

        Returns:
            Clipped GeoDataFrame within district boundary
        """
        if gdf.empty or boundary.empty:
            return gdf

        try:
            # Ensure both datasets have same CRS
            if boundary.crs != gdf.crs:
                boundary = boundary.to_crs(gdf.crs)

            clipped_gdf = gpd.clip(gdf, boundary)

            logger.debug(
                f"Clipped dataset: {len(gdf)} → {len(clipped_gdf)} features",
                extra={"original_features": len(gdf), "clipped_features": len(clipped_gdf)},
            )

            return clipped_gdf

        except Exception as e:
            logger.warning(f"Clipping failed, using original dataset: {str(e)}")
            return gdf

    def _validate_geometries(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Validate and clean invalid geometries using buffer(0) method.

        Args:
            gdf: GeoDataFrame with potentially invalid geometries

        Returns:
            GeoDataFrame with validated and cleaned geometries
        """
        if gdf.empty:
            return gdf

        # Check for invalid geometries
        invalid_mask = ~gdf.geometry.is_valid
        invalid_count = invalid_mask.sum()

        if invalid_count > 0:
            logger.warning(
                f"Found {invalid_count} invalid geometries, cleaning with buffer(0)",
                extra={"invalid_geometries": invalid_count, "total_features": len(gdf)},
            )

            # Clean invalid geometries using buffer(0)
            gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)

            # Verify cleaning worked
            still_invalid = (~gdf.geometry.is_valid).sum()
            if still_invalid > 0:
                logger.error(f"Failed to clean {still_invalid} geometries, removing them")
                gdf = gdf[gdf.geometry.is_valid]

        return gdf

    def _standardize_schema(
        self, gdf: gpd.GeoDataFrame, dataset_type: str, source_system: str, target_district: str
    ) -> gpd.GeoDataFrame:
        """
        Apply standardized schema while preserving original attributes.

        Args:
            gdf: Input GeoDataFrame with original schema
            dataset_type: Type of dataset (bezirksgrenzen, gebaeude, oepnv_haltestellen)
            source_system: Source system (geoportal, osm)
            target_district: District name for context

        Returns:
            GeoDataFrame with standardized schema and preserved original attributes
        """
        if gdf.empty:
            # Create empty GeoDataFrame with proper geometry column
            empty_gdf = gpd.GeoDataFrame(columns=list(STANDARD_SCHEMA.keys()), crs=TARGET_CRS)
            empty_gdf["geometry"] = gpd.GeoSeries([], crs=TARGET_CRS)
            return empty_gdf

        # Store original columns (excluding geometry)
        original_columns = [col for col in gdf.columns if col != "geometry"]
        if original_columns:
            original_attributes = gdf[original_columns].to_dict(orient="records")
        else:
            original_attributes = [{}] * len(gdf)

        # Create standardized DataFrame
        standardized_data = {
            "feature_id": [f"{dataset_type}_{i}" for i in range(len(gdf))],
            "dataset_type": [dataset_type] * len(gdf),
            "source_system": [source_system] * len(gdf),
            "bezirk": [target_district] * len(gdf),
            "geometry": gdf.geometry.values,  # Ensure proper array format
            "original_attributes": original_attributes,
        }

        return gpd.GeoDataFrame(standardized_data, crs=gdf.crs)

    def _calculate_quality_stats(
        self, harmonized_gdf: gpd.GeoDataFrame, processing_stats: dict[str, Any]  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Calculate comprehensive quality assurance statistics.

        Args:
            harmonized_gdf: Final harmonized GeoDataFrame
            processing_stats: Processing statistics from harmonization

        Returns:
            Dictionary with quality assurance metrics
        """
        if harmonized_gdf.empty:
            return {
                "total_features": 0,
                "geometry_validity_score": 0.0,
                "spatial_coverage_percentage": 0.0,
                "attribute_completeness_score": 0.0,
                "datasets_by_type": {},
                "crs_consistency": True,
                "quality_score": 0.0,
            }

        # Basic counts
        total_features = len(harmonized_gdf)

        # Geometry validity
        valid_geometries = harmonized_gdf.geometry.is_valid.sum()
        geometry_validity_score = valid_geometries / total_features if total_features > 0 else 0.0

        # Dataset type distribution
        datasets_by_type = harmonized_gdf["dataset_type"].value_counts().to_dict()

        # Spatial coverage (based on feature density)
        try:
            total_bounds = harmonized_gdf.total_bounds
            spatial_extent = [
                float(total_bounds[0]),
                float(total_bounds[1]),
                float(total_bounds[2]),
                float(total_bounds[3]),
            ]

            # Simple coverage metric based on feature count
            spatial_coverage_percentage = min(100.0, (total_features / 1000) * 100)
        except Exception:
            spatial_extent = None
            spatial_coverage_percentage = 0.0

        # Attribute completeness for key fields
        key_fields = ["feature_id", "dataset_type", "source_system", "bezirk"]
        completeness_scores = {}
        for field in key_fields:
            if field in harmonized_gdf.columns:
                non_null_count = harmonized_gdf[field].notna().sum()
                completeness_scores[field] = non_null_count / total_features

        attribute_completeness_score = sum(completeness_scores.values()) / len(completeness_scores)

        # Overall quality score (weighted average)
        quality_score = (
            geometry_validity_score * 0.4
            + attribute_completeness_score * 0.4
            + (spatial_coverage_percentage / 100) * 0.2
        )

        return {
            "total_features": total_features,
            "geometry_validity_score": round(geometry_validity_score, 3),
            "spatial_coverage_percentage": round(spatial_coverage_percentage, 2),
            "attribute_completeness_score": round(attribute_completeness_score, 3),
            "datasets_by_type": datasets_by_type,
            "crs_consistency": True,  # Always true after standardization
            "quality_score": round(quality_score, 3),
            "spatial_extent": spatial_extent,
            "field_completeness": {k: round(v, 3) for k, v in completeness_scores.items()},
        }


class ProcessingError(Exception):
    """Base exception for processing service failures."""

    pass

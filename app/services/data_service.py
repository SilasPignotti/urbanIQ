"""
Data Service for orchestrating geodata acquisition from multiple external sources.

Coordinates parallel data fetching from Berlin Geoportal WFS and OpenStreetMap Overpass API
with automatic district boundary loading, error resilience, and runtime statistics collection.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import geopandas as gpd

from app.connectors import (
    BuildingsConnector,
    ConnectorError,
    DistrictBoundariesConnector,
    OverpassConnector,
)
from app.models.job import JobStatus

logger = logging.getLogger("urbaniq.data_service")

# Dataset to connector mapping for MVP scope
DATASET_CONNECTOR_MAPPING = {
    "bezirksgrenzen": DistrictBoundariesConnector,  # Always retrieved
    "gebaeude": BuildingsConnector,
    "oepnv_haltestellen": OverpassConnector,
}

# Predefined metadata for each dataset type
DATASET_METADATA = {
    "bezirksgrenzen": {
        "name": "Bezirksgrenzen Berlin",
        "description": "Administrative district boundaries",
        "license": "CC BY 3.0 DE",
        "update_frequency": "monthly",
    },
    "gebaeude": {
        "name": "Gebäudedaten Berlin",
        "description": "Building footprints and usage data",
        "license": "CC BY 3.0 DE",
        "update_frequency": "quarterly",
    },
    "oepnv_haltestellen": {
        "name": "ÖPNV-Haltestellen Berlin",
        "description": "Public transport stops from OpenStreetMap",
        "license": "Open Database License (ODbL)",
        "update_frequency": "daily",
    },
}


class DataService:
    """
    Orchestrates geodata acquisition from multiple external sources.

    Coordinates parallel data fetching from Berlin Geoportal WFS and OpenStreetMap
    with automatic district boundary loading, error resilience, and runtime statistics.
    """

    def __init__(self) -> None:
        """Initialize Data Service with connector instances."""
        self._district_connector = DistrictBoundariesConnector()
        self._buildings_connector = BuildingsConnector()
        self._osm_connector = OverpassConnector()
        self._connector_instances = {
            "bezirksgrenzen": self._district_connector,
            "gebaeude": self._buildings_connector,
            "oepnv_haltestellen": self._osm_connector,
        }

    async def fetch_datasets_for_request(
        self, bezirk: str, datasets: list[str], job_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Orchestrate parallel data acquisition with automatic district boundary retrieval.

        Args:
            bezirk: Berlin district name (e.g., 'Pankow', 'Mitte')
            datasets: Requested datasets ['gebaeude', 'oepnv_haltestellen']
            job_id: Optional job ID for status tracking

        Returns:
            List of dataset dictionaries with geodata, metadata, and statistics

        Raises:
            ConnectorError: If district boundary fetch fails (required for all requests)
        """
        logger.info(
            f"Starting data acquisition for bezirk: {bezirk}, datasets: {datasets}",
            extra={"job_id": job_id, "bezirk": bezirk, "datasets": datasets},
        )

        # Always include district boundary (required for spatial filtering)
        all_datasets = ["bezirksgrenzen"] + [ds for ds in datasets if ds != "bezirksgrenzen"]

        # Update job status to processing if job_id provided
        if job_id:
            await self._update_job_status(job_id, JobStatus.PROCESSING, 10)

        # Execute parallel connector requests
        start_time = datetime.now()
        dataset_results = await self._execute_parallel_fetch(bezirk, all_datasets, job_id)

        # Calculate overall processing time
        processing_duration = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"Data acquisition completed in {processing_duration:.0f}ms. "
            f"Retrieved {len(dataset_results)} datasets",
            extra={
                "job_id": job_id,
                "processing_duration_ms": processing_duration,
                "successful_datasets": len(dataset_results),
            },
        )

        return dataset_results

    async def _execute_parallel_fetch(
        self, bezirk: str, datasets: list[str], job_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute parallel data fetching with error resilience.

        Args:
            bezirk: Berlin district name
            datasets: List of datasets to fetch (including bezirksgrenzen)
            job_id: Optional job ID for progress tracking

        Returns:
            List of successful dataset results

        Raises:
            ConnectorError: If district boundary fetch fails
        """
        # Create parallel tasks for all datasets
        tasks = []
        task_dataset_mapping = {}

        for dataset in datasets:
            if dataset in DATASET_CONNECTOR_MAPPING:
                task = self._fetch_single_dataset(bezirk, dataset)
                tasks.append(task)
                task_dataset_mapping[id(task)] = dataset
            else:
                logger.warning(f"Unknown dataset type: {dataset}", extra={"dataset": dataset})

        # Execute all tasks in parallel with exception handling
        logger.debug(f"Executing {len(tasks)} parallel connector requests")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle partial failures
        successful_results: list[dict[str, Any]] = []
        failed_datasets = []

        for i, result in enumerate(results):
            task = tasks[i]
            dataset = task_dataset_mapping[id(task)]

            if isinstance(result, Exception):
                # Handle connector failure
                error_msg = str(result)
                logger.error(
                    f"Connector failed for dataset {dataset}: {error_msg}",
                    extra={"dataset": dataset, "bezirk": bezirk, "error": error_msg},
                )

                # District boundary failure is critical - abort entire request
                if dataset == "bezirksgrenzen":
                    logger.error(
                        "District boundary fetch failed - aborting request",
                        extra={"bezirk": bezirk, "error": error_msg},
                    )
                    if job_id:
                        await self._update_job_status(
                            job_id,
                            JobStatus.FAILED,
                            0,
                            f"District boundary fetch failed: {error_msg}",
                        )
                    raise ConnectorError(
                        f"Failed to fetch district boundary for {bezirk}: {error_msg}"
                    )

                failed_datasets.append(dataset)
            else:
                # Successful result - type checked
                if isinstance(result, dict):
                    successful_results.append(result)
                    logger.debug(
                        f"Successfully fetched dataset: {dataset}",
                        extra={
                            "dataset": dataset,
                            "feature_count": result["runtime_stats"]["feature_count"],
                        },
                    )

        # Update job progress based on successful vs total datasets
        if job_id:
            progress = min(90, int((len(successful_results) / len(datasets)) * 80) + 10)
            await self._update_job_status(job_id, JobStatus.PROCESSING, progress)

        # Log summary of partial failures
        if failed_datasets:
            logger.warning(
                f"Partial failure: {len(failed_datasets)} datasets failed, "
                f"{len(successful_results)} succeeded",
                extra={
                    "failed_datasets": failed_datasets,
                    "successful_count": len(successful_results),
                    "bezirk": bezirk,
                },
            )

        return successful_results

    async def _fetch_single_dataset(self, bezirk: str, dataset_type: str) -> dict[str, Any]:
        """
        Fetch data from a single connector with runtime statistics collection.

        Args:
            bezirk: Berlin district name
            dataset_type: Type of dataset to fetch

        Returns:
            Dataset dictionary with geodata, metadata, and runtime statistics

        Raises:
            ConnectorError: If connector request fails
        """
        if dataset_type not in self._connector_instances:
            raise ConnectorError(f"Unsupported dataset type: {dataset_type}")

        start_time = datetime.now()

        try:
            # Fetch data using appropriate connector method
            if dataset_type == "bezirksgrenzen":
                # Type-checked call to district connector
                geodata = await self._district_connector.fetch_district_boundary(bezirk)
            elif dataset_type == "gebaeude":
                # First get district boundary for spatial filtering
                district_gdf = await self._district_connector.fetch_district_boundary(bezirk)
                geodata = await self._buildings_connector.fetch_buildings(district_gdf)
            elif dataset_type == "oepnv_haltestellen":
                # First get district boundary for spatial filtering
                district_gdf = await self._district_connector.fetch_district_boundary(bezirk)
                geodata = await self._osm_connector.fetch_transport_stops(district_gdf)
            else:
                raise ConnectorError(f"Unsupported dataset type: {dataset_type}")

            # Calculate runtime statistics
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            runtime_stats = self._calculate_runtime_stats(geodata, response_time_ms, "success")

            # Create standardized dataset result
            return {
                "dataset_id": f"{dataset_type}_{bezirk.lower()}",
                "dataset_type": dataset_type,
                "source": "geoportal" if dataset_type != "oepnv_haltestellen" else "osm",
                "geodata": geodata,
                "predefined_metadata": DATASET_METADATA[dataset_type],
                "runtime_stats": runtime_stats,
            }

        except Exception as e:
            # Calculate runtime stats for failed request
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"Dataset fetch failed: {dataset_type} for {bezirk}",
                extra={
                    "dataset_type": dataset_type,
                    "bezirk": bezirk,
                    "response_time_ms": response_time_ms,
                    "error": str(e),
                },
            )
            raise ConnectorError(f"Failed to fetch {dataset_type} for {bezirk}: {str(e)}") from e

    def _calculate_runtime_stats(
        self, geodata: gpd.GeoDataFrame, response_time_ms: float, status: str
    ) -> dict[str, Any]:
        """
        Calculate runtime statistics for a dataset.

        Args:
            geodata: GeoDataFrame with fetched data
            response_time_ms: Response time in milliseconds
            status: Connector status ('success', 'failed', 'partial')

        Returns:
            Runtime statistics dictionary
        """
        if geodata.empty:
            return {
                "response_time_ms": int(response_time_ms),
                "feature_count": 0,
                "spatial_extent": None,
                "coverage_percentage": 0.0,
                "data_quality_score": 0.0,
                "connector_status": status,
                "error_message": None if status == "success" else "No features returned",
                "request_timestamp": datetime.now(),
                "processing_duration_ms": int(response_time_ms),
            }

        # Calculate spatial extent (bbox)
        bounds = geodata.total_bounds
        spatial_extent = [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]

        # Calculate data quality score based on completeness
        total_features = len(geodata)
        features_with_geometry = len(geodata.dropna(subset=["geometry"]))
        data_quality_score = features_with_geometry / total_features if total_features > 0 else 0.0

        # Calculate coverage percentage (simplified - based on feature density)
        coverage_percentage = (
            min(100.0, (total_features / 1000) * 100) if total_features > 0 else 0.0
        )

        return {
            "response_time_ms": int(response_time_ms),
            "feature_count": total_features,
            "spatial_extent": spatial_extent,
            "coverage_percentage": round(coverage_percentage, 2),
            "data_quality_score": round(data_quality_score, 2),
            "connector_status": status,
            "error_message": None,
            "request_timestamp": datetime.now(),
            "processing_duration_ms": int(response_time_ms),
        }

    async def _update_job_status(
        self, job_id: str, status: JobStatus, progress: int, error_message: str | None = None
    ) -> None:
        """
        Update job status and progress.

        Args:
            job_id: Job identifier
            status: New job status
            progress: Progress percentage (0-100)
            error_message: Optional error message for failed status
        """
        # Note: This is a simplified implementation
        # In a real application, this would interact with the database
        # through a repository pattern or database session
        logger.info(
            f"Job status update: {job_id} -> {status.value} ({progress}%)",
            extra={
                "job_id": job_id,
                "status": status.value,
                "progress": progress,
                "error_message": error_message,
            },
        )

    async def test_connector_health(self) -> dict[str, bool]:
        """
        Test health of all connectors.

        Returns:
            Dictionary mapping connector names to health status
        """
        logger.info("Testing connector health")

        # Test all connectors in parallel
        health_tasks = [
            self._test_single_connector_health("district", self._district_connector),
            self._test_single_connector_health("buildings", self._buildings_connector),
            self._test_single_connector_health("osm", self._osm_connector),
        ]

        results = await asyncio.gather(*health_tasks, return_exceptions=True)

        health_status = {}
        connector_names = ["district", "buildings", "osm"]

        for i, result in enumerate(results):
            connector_name = connector_names[i]
            if isinstance(result, Exception):
                health_status[connector_name] = False
                logger.error(f"Health check failed for {connector_name}: {result}")
            else:
                # Type check the boolean result
                health_status[connector_name] = bool(result)

        logger.info(f"Connector health check completed: {health_status}")
        return health_status

    async def _test_single_connector_health(
        self, name: str, connector: DistrictBoundariesConnector | BuildingsConnector | OverpassConnector
    ) -> bool:
        """
        Test health of a single connector.

        Args:
            name: Connector name for logging
            connector: Connector instance

        Returns:
            True if healthy, False otherwise
        """
        try:
            return await connector.test_connection()
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            return False

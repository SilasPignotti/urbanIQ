"""
Additional Berlin Geoportal WFS connectors for population and building data.

Implements connectors for population density and building floors data
with spatial filtering, CRS handling, and multi-layer support.
"""

import logging
from io import StringIO

import geopandas as gpd
import pandas as pd

from .base import BaseConnector

logger = logging.getLogger("urbaniq.connectors.geoportal_extended2")

# WFS base parameters for Berlin Geoportal
BASE_WFS_PARAMS = {
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "OUTPUTFORMAT": "application/json",
    "SRSNAME": "EPSG:25833",  # Berlin's standard CRS
}


class PopulationDensityConnector(BaseConnector):
    """
    Connector for Berlin population density (Einwohnerdichte) 2024 from WFS.

    Fetches population density data for demographic analysis and urban planning.
    """

    def __init__(self) -> None:
        """Initialize population density connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/ua_einwohnerdichte_2024",
            timeout=60.0,  # Population data can be substantial
        )

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal population density WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Population density connection test failed: {str(e)}")
            return False

    async def fetch_population_density(
        self, district_boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Fetch population density data within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with population density clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching population density data for district")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "ua_einwohnerdichte_2024:ua_einwohnerdichte_2024",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            population_gdf = gpd.read_file(StringIO(response_text))

            if population_gdf.empty:
                logger.warning("No population density data found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if population_gdf.crs is None:
                population_gdf.set_crs("EPSG:25833", inplace=True)
            elif population_gdf.crs != "EPSG:25833":
                population_gdf = population_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_population = gpd.clip(population_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_population = population_gdf

            logger.info(
                f"Successfully fetched {len(clipped_population)} population density features"
            )
            return clipped_population

        except Exception as e:
            error_msg = f"Failed to fetch population density: {str(e)}"
            logger.error(error_msg)
            raise

    def _create_bbox_filter(self, district_gdf: gpd.GeoDataFrame) -> str:
        """
        Create BBOX filter string from district boundary.

        Args:
            district_gdf: GeoDataFrame with district boundary

        Returns:
            BBOX parameter string in format: minx,miny,maxx,maxy,EPSG:25833
        """
        bounds = district_gdf.total_bounds
        minx, miny, maxx, maxy = bounds

        # Add small buffer to ensure we don't miss edge cases
        buffer = 100  # 100 meters buffer in EPSG:25833
        bbox_str = f"{minx - buffer},{miny - buffer},{maxx + buffer},{maxy + buffer},EPSG:25833"

        logger.debug(f"Created BBOX filter: {bbox_str}")
        return bbox_str


class BuildingFloorsConnector(BaseConnector):
    """
    Connector for Berlin building floors (Gebäudegeschosse) from WFS.

    Fetches building floor data categorized by floor ranges for urban planning
    and density analysis.
    """

    def __init__(self) -> None:
        """Initialize building floors connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/gebaeude_geschosse",
            timeout=120.0,  # Building floors data can be very large
        )
        # Floor range layer mapping as specified in PRP
        self.floor_layers = {
            "more_than_10": "a_geschosszahl_mehr_10",
            "7_to_10": "b_geschosszahl_7_10",
            "5_to_6": "c_geschosszahl_5_6",
            "3_to_4": "d_geschosszahl_3_4",
            "1_to_2": "e_geschosszahl_1_2",
            "under_1": "f_geschosszahl_unter_1",
        }

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal building floors WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Building floors connection test failed: {str(e)}")
            return False

    async def fetch_all_building_floors(
        self, district_boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Fetch all building floors data from all floor range layers.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with all building floors clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching all building floors data for district")

        all_floors_gdfs = []

        # Fetch data from each floor range layer
        for floor_range, layer_name in self.floor_layers.items():
            try:
                floor_gdf = await self._fetch_floor_layer(
                    district_boundary, layer_name, floor_range
                )
                if not floor_gdf.empty:
                    all_floors_gdfs.append(floor_gdf)
            except Exception as e:
                logger.warning(f"Failed to fetch {floor_range} floors: {str(e)}")
                continue

        if not all_floors_gdfs:
            logger.warning("No building floors data found in any layer")
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

        # Combine all floor data
        combined_gdf = pd.concat(all_floors_gdfs, ignore_index=True)

        # Ensure result is a GeoDataFrame with correct CRS
        if not isinstance(combined_gdf, gpd.GeoDataFrame):
            combined_gdf = gpd.GeoDataFrame(combined_gdf, crs="EPSG:25833")
        elif combined_gdf.crs != "EPSG:25833":
            combined_gdf = combined_gdf.to_crs("EPSG:25833")

        logger.info(
            f"Successfully fetched {len(combined_gdf)} building floors features from all layers"
        )
        return combined_gdf

    async def fetch_specific_floor_range(
        self, district_boundary: gpd.GeoDataFrame, floor_range: str
    ) -> gpd.GeoDataFrame:
        """
        Fetch building floors for a specific floor range.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry
            floor_range: Floor range key (e.g., "more_than_10", "7_to_10")

        Returns:
            GeoDataFrame with buildings in specified floor range in EPSG:25833

        Raises:
            ConnectorError: If request fails
            ValueError: If floor_range is invalid
        """
        if floor_range not in self.floor_layers:
            raise ValueError(
                f"Invalid floor range: {floor_range}. Valid options: {list(self.floor_layers.keys())}"
            )

        layer_name = self.floor_layers[floor_range]
        return await self._fetch_floor_layer(district_boundary, layer_name, floor_range)

    async def _fetch_floor_layer(
        self, district_boundary: gpd.GeoDataFrame, layer_name: str, floor_range: str
    ) -> gpd.GeoDataFrame:
        """
        Fetch data from a specific building floors layer.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry
            layer_name: WFS layer name
            floor_range: Floor range identifier for metadata

        Returns:
            GeoDataFrame with building floors from specified layer in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        logger.info(f"Fetching building floors for range: {floor_range}")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": layer_name,
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            floors_gdf = gpd.read_file(StringIO(response_text))

            if floors_gdf.empty:
                logger.warning(f"No building floors found for range {floor_range}")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Add floor range metadata
            floors_gdf["floor_range"] = floor_range

            # Ensure CRS is set correctly
            if floors_gdf.crs is None:
                floors_gdf.set_crs("EPSG:25833", inplace=True)
            elif floors_gdf.crs != "EPSG:25833":
                floors_gdf = floors_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_floors = gpd.clip(floors_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_floors = floors_gdf

            logger.info(
                f"Successfully fetched {len(clipped_floors)} buildings for floor range {floor_range}"
            )
            return clipped_floors

        except Exception as e:
            error_msg = f"Failed to fetch building floors for range {floor_range}: {str(e)}"
            logger.error(error_msg)
            raise

    def _create_bbox_filter(self, district_gdf: gpd.GeoDataFrame) -> str:
        """
        Create BBOX filter string from district boundary.

        Args:
            district_gdf: GeoDataFrame with district boundary

        Returns:
            BBOX parameter string in format: minx,miny,maxx,maxy,EPSG:25833
        """
        bounds = district_gdf.total_bounds
        minx, miny, maxx, maxy = bounds

        # Add small buffer to ensure we don't miss edge cases
        buffer = 100  # 100 meters buffer in EPSG:25833
        bbox_str = f"{minx - buffer},{miny - buffer},{maxx + buffer},{maxy + buffer},EPSG:25833"

        logger.debug(f"Created BBOX filter: {bbox_str}")
        return bbox_str

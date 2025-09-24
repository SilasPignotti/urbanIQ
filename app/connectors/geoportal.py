"""
Berlin Geoportal WFS connectors for geodata acquisition.

Implements connectors for district boundaries and buildings data
with spatial filtering, CRS handling, and GeoDataFrame integration.
"""

import logging
from io import StringIO

import geopandas as gpd

from .base import BaseConnector

logger = logging.getLogger("urbaniq.connectors.geoportal")

# WFS base parameters for Berlin Geoportal
BASE_WFS_PARAMS = {
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "OUTPUTFORMAT": "application/json",
    "SRSNAME": "EPSG:25833",  # Berlin's standard CRS
}


class DistrictBoundariesConnector(BaseConnector):
    """
    Connector for Berlin district boundaries (Bezirksgrenzen) from ALKIS WFS.

    Fetches administrative district boundaries for spatial filtering
    and geographic context in urban planning analyses.
    """

    def __init__(self) -> None:
        """Initialize district boundaries connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/alkis_bezirke",
            timeout=30.0,  # District boundaries are small, should be fast
        )
        self.layer_name = "alkis_bezirke:bezirksgrenzen"

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    async def fetch_district_boundary(self, bezirk_name: str) -> gpd.GeoDataFrame:
        """
        Fetch boundary geometry for a specific Berlin district.

        Args:
            bezirk_name: Name of the Berlin district (e.g., 'Pankow', 'Mitte')

        Returns:
            GeoDataFrame with district boundary geometry in EPSG:25833

        Raises:
            ConnectorError: If district not found or request fails
        """
        logger.info(f"Fetching district boundary for: {bezirk_name}")

        # Build WFS request parameters with CQL filter for district name
        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": self.layer_name,
            "CQL_FILTER": f"namgem='{bezirk_name}'",
        }

        try:
            # Make WFS request
            response_text = await self._get_text(self.base_url, params=params)

            # Parse GeoJSON response into GeoDataFrame
            gdf = gpd.read_file(StringIO(response_text))

            if gdf.empty:
                raise ValueError(f"District '{bezirk_name}' not found in WFS service")

            # Ensure CRS is set correctly
            if gdf.crs is None:
                gdf.set_crs("EPSG:25833", inplace=True)
            elif gdf.crs != "EPSG:25833":
                gdf = gdf.to_crs("EPSG:25833")

            logger.info(f"Successfully fetched {len(gdf)} boundary feature(s) for {bezirk_name}")
            return gdf

        except Exception as e:
            error_msg = f"Failed to fetch district boundary for {bezirk_name}: {str(e)}"
            logger.error(error_msg)
            raise

    async def fetch_all_districts(self) -> gpd.GeoDataFrame:
        """
        Fetch all Berlin district boundaries.

        Returns:
            GeoDataFrame with all district boundaries in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        logger.info("Fetching all Berlin district boundaries")

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": self.layer_name,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            gdf = gpd.read_file(StringIO(response_text))

            if gdf.empty:
                raise ValueError("No district boundaries found in WFS service")

            # Ensure CRS is set correctly
            if gdf.crs is None:
                gdf.set_crs("EPSG:25833", inplace=True)
            elif gdf.crs != "EPSG:25833":
                gdf = gdf.to_crs("EPSG:25833")

            logger.info(f"Successfully fetched {len(gdf)} district boundaries")
            return gdf

        except Exception as e:
            error_msg = f"Failed to fetch all district boundaries: {str(e)}"
            logger.error(error_msg)
            raise


class BuildingsConnector(BaseConnector):
    """
    Connector for Berlin building data (Gebäude) from ALKIS WFS.

    Fetches building footprints and attributes with spatial filtering
    using bounding boxes to handle large datasets efficiently.
    """

    def __init__(self) -> None:
        """Initialize buildings connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/alkis_gebaeude",
            timeout=120.0,  # Buildings datasets can be very large
        )
        self.layer_name = "alkis_gebaeude:gebaeude"

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal buildings WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Buildings connection test failed: {str(e)}")
            return False

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

        buffer = 100  # 100 meters buffer in EPSG:25833
        bbox_str = f"{minx - buffer},{miny - buffer},{maxx + buffer},{maxy + buffer},EPSG:25833"

        logger.debug(f"Created BBOX filter: {bbox_str}")
        return bbox_str

    async def fetch_buildings(self, district_boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Fetch building data within district boundary with spatial filtering.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with buildings clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info(
            f"Fetching buildings for district boundary with {len(district_boundary)} feature(s)"
        )

        # Create BBOX parameter for spatial filtering
        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": self.layer_name,
            "BBOX": bbox_filter,
        }

        try:
            # Make WFS request
            response_text = await self._get_text(self.base_url, params=params)

            # Parse GeoJSON response
            buildings_gdf = gpd.read_file(StringIO(response_text))

            # Handle empty results
            if buildings_gdf.empty:
                logger.warning("No buildings found in specified area")
                # Return empty GeoDataFrame with correct CRS
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if buildings_gdf.crs is None:
                buildings_gdf.set_crs("EPSG:25833", inplace=True)
            elif buildings_gdf.crs != "EPSG:25833":
                buildings_gdf = buildings_gdf.to_crs("EPSG:25833")

            # Ensure district boundary has same CRS
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            # Clip buildings to exact district boundary (more precise than BBOX)
            try:
                clipped_buildings = gpd.clip(buildings_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_buildings = buildings_gdf

            logger.info(
                f"Successfully fetched {len(clipped_buildings)} buildings "
                f"(from {len(buildings_gdf)} in BBOX)"
            )

            return clipped_buildings

        except Exception as e:
            error_msg = f"Failed to fetch buildings: {str(e)}"
            logger.error(error_msg)
            raise

    async def fetch_buildings_sample(
        self, district_boundary: gpd.GeoDataFrame, max_features: int = 1000
    ) -> gpd.GeoDataFrame:
        """
        Fetch a sample of buildings for testing or preview purposes.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry
            max_features: Maximum number of buildings to return

        Returns:
            GeoDataFrame with sample buildings in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        logger.info(f"Fetching buildings sample (max {max_features} features)")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": self.layer_name,
            "BBOX": bbox_filter,
            "COUNT": str(max_features),
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            buildings_gdf = gpd.read_file(StringIO(response_text))

            if buildings_gdf.empty:
                logger.warning("No buildings found in sample area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS
            if buildings_gdf.crs is None:
                buildings_gdf.set_crs("EPSG:25833", inplace=True)
            elif buildings_gdf.crs != "EPSG:25833":
                buildings_gdf = buildings_gdf.to_crs("EPSG:25833")

            logger.info(f"Successfully fetched {len(buildings_gdf)} buildings in sample")
            return buildings_gdf

        except Exception as e:
            error_msg = f"Failed to fetch buildings sample: {str(e)}"
            logger.error(error_msg)
            raise


class CyclingNetworkConnector(BaseConnector):
    """
    Connector for Berlin cycling network (Radverkehrsnetz) from WFS.

    Fetches cycling infrastructure including main network and long-distance routes
    for mobility analysis and transport planning.
    """

    def __init__(self) -> None:
        """Initialize cycling network connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/radverkehrsnetz",
            timeout=60.0,  # Cycling network data can be substantial
        )

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal cycling network WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Cycling network connection test failed: {str(e)}")
            return False

    async def fetch_cycling_network(self, district_boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Fetch cycling network data within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with cycling network clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching cycling network data for district")

        # Create BBOX parameter for spatial filtering
        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "radverkehrsnetz:radverkehrsnetz",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            cycling_gdf = gpd.read_file(StringIO(response_text))

            if cycling_gdf.empty:
                logger.warning("No cycling network found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if cycling_gdf.crs is None:
                cycling_gdf.set_crs("EPSG:25833", inplace=True)
            elif cycling_gdf.crs != "EPSG:25833":
                cycling_gdf = cycling_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_cycling = gpd.clip(cycling_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_cycling = cycling_gdf

            logger.info(f"Successfully fetched {len(clipped_cycling)} cycling network features")
            return clipped_cycling

        except Exception as e:
            error_msg = f"Failed to fetch cycling network: {str(e)}"
            logger.error(error_msg)
            raise

    async def fetch_long_distance_routes(
        self, district_boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Fetch long-distance cycling routes within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with long-distance routes clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching long-distance cycling routes for district")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "radverkehrsnetz:radfernwege",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            routes_gdf = gpd.read_file(StringIO(response_text))

            if routes_gdf.empty:
                logger.warning("No long-distance cycling routes found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if routes_gdf.crs is None:
                routes_gdf.set_crs("EPSG:25833", inplace=True)
            elif routes_gdf.crs != "EPSG:25833":
                routes_gdf = routes_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_routes = gpd.clip(routes_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_routes = routes_gdf

            logger.info(f"Successfully fetched {len(clipped_routes)} long-distance cycling routes")
            return clipped_routes

        except Exception as e:
            error_msg = f"Failed to fetch long-distance cycling routes: {str(e)}"
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

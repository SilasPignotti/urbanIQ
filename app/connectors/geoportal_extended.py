"""
Extended Berlin Geoportal WFS connectors for additional geodata sources.

Implements connectors for cycling networks, street networks, Ortsteile boundaries,
population density, and building floors data with spatial filtering and CRS handling.
"""

import logging
from io import StringIO

import geopandas as gpd

from .base import BaseConnector

logger = logging.getLogger("urbaniq.connectors.geoportal_extended")

# WFS base parameters for Berlin Geoportal
BASE_WFS_PARAMS = {
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "OUTPUTFORMAT": "application/json",
    "SRSNAME": "EPSG:25833",  # Berlin's standard CRS
}


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


class StreetNetworkConnector(BaseConnector):
    """
    Connector for Berlin street network (Straßennetz) from WFS.

    Fetches street network infrastructure including segments, connection points,
    and structures for mobility analysis and routing applications.
    """

    def __init__(self) -> None:
        """Initialize street network connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/detailnetz",
            timeout=90.0,  # Street network data can be very large
        )

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal street network WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Street network connection test failed: {str(e)}")
            return False

    async def fetch_street_segments(self, district_boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Fetch street segments within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with street segments clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching street segments for district")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "detailnetz:c_strassenabschnitte",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            streets_gdf = gpd.read_file(StringIO(response_text))

            if streets_gdf.empty:
                logger.warning("No street segments found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if streets_gdf.crs is None:
                streets_gdf.set_crs("EPSG:25833", inplace=True)
            elif streets_gdf.crs != "EPSG:25833":
                streets_gdf = streets_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_streets = gpd.clip(streets_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_streets = streets_gdf

            logger.info(f"Successfully fetched {len(clipped_streets)} street segments")
            return clipped_streets

        except Exception as e:
            error_msg = f"Failed to fetch street segments: {str(e)}"
            logger.error(error_msg)
            raise

    async def fetch_connection_points(
        self, district_boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Fetch street connection points/intersections within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with connection points clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching street connection points for district")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "detailnetz:a_verbindungspunkte",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            points_gdf = gpd.read_file(StringIO(response_text))

            if points_gdf.empty:
                logger.warning("No connection points found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if points_gdf.crs is None:
                points_gdf.set_crs("EPSG:25833", inplace=True)
            elif points_gdf.crs != "EPSG:25833":
                points_gdf = points_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_points = gpd.clip(points_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_points = points_gdf

            logger.info(f"Successfully fetched {len(clipped_points)} connection points")
            return clipped_points

        except Exception as e:
            error_msg = f"Failed to fetch connection points: {str(e)}"
            logger.error(error_msg)
            raise

    async def fetch_street_structures(
        self, district_boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Fetch street structures (bridges, tunnels) within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with street structures clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching street structures for district")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "detailnetz:b_bauwerke",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            structures_gdf = gpd.read_file(StringIO(response_text))

            if structures_gdf.empty:
                logger.warning("No street structures found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if structures_gdf.crs is None:
                structures_gdf.set_crs("EPSG:25833", inplace=True)
            elif structures_gdf.crs != "EPSG:25833":
                structures_gdf = structures_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_structures = gpd.clip(structures_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_structures = structures_gdf

            logger.info(f"Successfully fetched {len(clipped_structures)} street structures")
            return clipped_structures

        except Exception as e:
            error_msg = f"Failed to fetch street structures: {str(e)}"
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


class OrtsteileBoundariesConnector(BaseConnector):
    """
    Connector for Berlin Ortsteile boundaries from WFS.

    Fetches sub-district administrative boundaries (Ortsteile) within Bezirke
    for detailed urban analysis and planning.
    """

    def __init__(self) -> None:
        """Initialize Ortsteile boundaries connector."""
        super().__init__(
            base_url="https://gdi.berlin.de/services/wfs/alkis_ortsteile",
            timeout=30.0,  # Ortsteile boundaries are relatively small
        )

    async def test_connection(self) -> bool:
        """
        Test connection to Berlin Geoportal Ortsteile WFS service.

        Returns:
            True if GetCapabilities request succeeds, False otherwise
        """
        try:
            params = {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            response = await self._make_request("GET", self.base_url, params=params)
            return response.status_code == 200 and "WFS_Capabilities" in response.text
        except Exception as e:
            logger.error(f"Ortsteile boundaries connection test failed: {str(e)}")
            return False

    async def fetch_ortsteile_boundaries(
        self, district_boundary: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Fetch Ortsteile boundaries within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with Ortsteile boundaries clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info("Fetching Ortsteile boundaries for district")

        bbox_filter = self._create_bbox_filter(district_boundary)

        params = {
            **BASE_WFS_PARAMS,
            "TYPENAMES": "alkis_ortsteile:ortsteile",
            "BBOX": bbox_filter,
        }

        try:
            response_text = await self._get_text(self.base_url, params=params)
            ortsteile_gdf = gpd.read_file(StringIO(response_text))

            if ortsteile_gdf.empty:
                logger.warning("No Ortsteile boundaries found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Ensure CRS is set correctly
            if ortsteile_gdf.crs is None:
                ortsteile_gdf.set_crs("EPSG:25833", inplace=True)
            elif ortsteile_gdf.crs != "EPSG:25833":
                ortsteile_gdf = ortsteile_gdf.to_crs("EPSG:25833")

            # Clip to exact district boundary
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            try:
                clipped_ortsteile = gpd.clip(ortsteile_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using BBOX-filtered results: {str(e)}")
                clipped_ortsteile = ortsteile_gdf

            logger.info(f"Successfully fetched {len(clipped_ortsteile)} Ortsteile boundaries")
            return clipped_ortsteile

        except Exception as e:
            error_msg = f"Failed to fetch Ortsteile boundaries: {str(e)}"
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

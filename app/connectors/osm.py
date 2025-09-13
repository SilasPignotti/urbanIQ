"""
OpenStreetMap Overpass API connector for public transport stops.

Implements connector for ÖPNV-Haltestellen (public transport stops) from OpenStreetMap
with rate limiting, query templates, CRS transformation, and spatial filtering.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

from .base import BaseConnector

logger = logging.getLogger("urbaniq.connectors.osm")


class OverpassRateLimiter:
    """
    Rate limiter for Overpass API requests.

    Enforces maximum 2 requests per second to comply with Overpass API guidelines.
    Thread-safe implementation for concurrent request handling.
    """

    def __init__(self, max_requests_per_second: float = 2.0) -> None:
        """
        Initialize rate limiter.

        Args:
            max_requests_per_second: Maximum allowed requests per second
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time: datetime | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make a request, enforcing rate limits.

        Blocks until it's safe to make the next request according to rate limits.
        """
        async with self._lock:
            now = datetime.now()

            if self.last_request_time is not None:
                elapsed = (now - self.last_request_time).total_seconds()

                if elapsed < self.min_interval:
                    sleep_time = self.min_interval - elapsed
                    logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
                    await asyncio.sleep(sleep_time)

            self.last_request_time = datetime.now()


class OverpassConnector(BaseConnector):
    """
    Connector for OpenStreetMap public transport stops via Overpass API.

    Fetches public transport stops (ÖPNV-Haltestellen) including bus stops,
    tram stops, and other public transport infrastructure with proper rate
    limiting, spatial filtering, and CRS transformation.
    """

    # Overpass query template for public transport stops
    TRANSPORT_STOPS_QUERY_TEMPLATE = """
    [out:json][timeout:{timeout}];
    (
      node["public_transport"="stop_position"]({bbox});
      node["highway"="bus_stop"]({bbox});
      node["railway"="tram_stop"]({bbox});
      node["railway"="station"]({bbox});
      node["amenity"="ferry_terminal"]({bbox});
    );
    out geom;
    """

    def __init__(self, timeout: float = 30.0, rate_limit_rps: float = 2.0) -> None:
        """
        Initialize Overpass API connector.

        Args:
            timeout: Request timeout in seconds
            rate_limit_rps: Rate limit in requests per second
        """
        super().__init__(base_url="https://overpass-api.de/api/interpreter", timeout=timeout)
        self.overpass_timeout = 25  # Overpass query timeout
        self.rate_limiter = OverpassRateLimiter(rate_limit_rps)

    async def test_connection(self) -> bool:
        """
        Test connection to Overpass API service.

        Returns:
            True if simple query succeeds, False otherwise
        """
        try:
            # Simple test query for a single node
            test_query = "[out:json][timeout:5]; node(1); out;"

            await self.rate_limiter.acquire()
            response = await self._make_request(
                "POST", self.base_url, data=test_query, headers={"Content-Type": "text/plain"}
            )

            # Check if response has expected Overpass structure
            data = response.json()
            return "elements" in data

        except Exception as e:
            logger.error(f"Overpass connection test failed: {str(e)}")
            return False

    def _create_bbox_filter(self, district_gdf: gpd.GeoDataFrame) -> str:
        """
        Create bbox filter string from district boundary for Overpass query.

        Args:
            district_gdf: GeoDataFrame with district boundary in any CRS

        Returns:
            Bbox string in format: south,west,north,east (WGS84 coordinates)
        """
        # Convert to WGS84 for OSM query
        if district_gdf.crs != "EPSG:4326":
            district_wgs84 = district_gdf.to_crs("EPSG:4326")
        else:
            district_wgs84 = district_gdf.copy()

        bounds = district_wgs84.total_bounds
        minx, miny, maxx, maxy = bounds

        # Add small buffer (approximately 100m in degrees)
        buffer_deg = 0.001  # ~111m at Berlin latitude

        # Overpass bbox format: south,west,north,east
        bbox_str = (
            f"{miny - buffer_deg},{minx - buffer_deg},{maxy + buffer_deg},{maxx + buffer_deg}"
        )

        logger.debug(f"Created Overpass bbox filter: {bbox_str}")
        return bbox_str

    def _process_overpass_response(self, response_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Process Overpass JSON response and extract transport stop features.

        Args:
            response_data: Parsed JSON response from Overpass API

        Returns:
            List of feature dictionaries with geometry and attributes
        """
        features = []
        elements = response_data.get("elements", [])

        logger.debug(f"Processing {len(elements)} elements from Overpass response")

        for element in elements:
            # Only process nodes with coordinates
            if element.get("type") != "node" or "lat" not in element or "lon" not in element:
                continue

            lat = element["lat"]
            lon = element["lon"]

            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                logger.warning(f"Invalid coordinates for element {element.get('id')}: {lat}, {lon}")
                continue

            # Extract and process OSM tags
            tags = element.get("tags", {})

            # Determine transport mode from tags
            transport_mode = self._determine_transport_mode(tags)

            # Create feature with standardized attributes
            feature = {
                "geometry": Point(lon, lat),
                "osm_id": element.get("id"),
                "name": tags.get("name", ""),
                "operator": tags.get("operator", ""),
                "transport_mode": transport_mode,
                "public_transport": tags.get("public_transport", ""),
                "highway": tags.get("highway", ""),
                "railway": tags.get("railway", ""),
                "amenity": tags.get("amenity", ""),
                "ref": tags.get("ref", ""),
                "network": tags.get("network", ""),
                # Store all original OSM tags for reference
                "osm_tags": json.dumps(tags) if tags else "",
            }

            features.append(feature)

        logger.info(f"Processed {len(features)} valid transport stops from Overpass response")
        return features

    def _determine_transport_mode(self, tags: dict[str, str]) -> str:
        """
        Determine primary transport mode from OSM tags.

        Args:
            tags: OSM tags dictionary

        Returns:
            Primary transport mode string
        """
        # Priority order for transport mode detection
        if tags.get("public_transport") == "stop_position":
            return "public_transport"
        elif tags.get("highway") == "bus_stop":
            return "bus"
        elif tags.get("railway") == "tram_stop":
            return "tram"
        elif tags.get("railway") == "station":
            return "rail_station"
        elif tags.get("amenity") == "ferry_terminal":
            return "ferry"
        else:
            return "unknown"

    async def fetch_transport_stops(self, district_boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Fetch public transport stops within district boundary.

        Args:
            district_boundary: GeoDataFrame with district boundary geometry

        Returns:
            GeoDataFrame with transport stops clipped to district boundary in EPSG:25833

        Raises:
            ConnectorError: If request fails or data is invalid
        """
        if district_boundary.empty:
            raise ValueError("District boundary GeoDataFrame is empty")

        logger.info(
            f"Fetching transport stops for district boundary with {len(district_boundary)} feature(s)"
        )

        # Create bbox filter for Overpass query
        bbox_filter = self._create_bbox_filter(district_boundary)

        # Build Overpass query from template
        query = self.TRANSPORT_STOPS_QUERY_TEMPLATE.format(
            timeout=self.overpass_timeout, bbox=bbox_filter
        ).strip()

        try:
            # Enforce rate limiting
            await self.rate_limiter.acquire()

            # Make Overpass API request
            logger.debug("Making Overpass API request")
            response = await self._make_request(
                "POST", self.base_url, data=query, headers={"Content-Type": "text/plain"}
            )

            # Parse JSON response
            try:
                response_data: dict[str, Any] = response.json()
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from Overpass API: {str(e)}") from e

            # Process response and extract features
            features = self._process_overpass_response(response_data)

            # Handle empty results
            if not features:
                logger.warning("No transport stops found in specified area")
                return gpd.GeoDataFrame(geometry=[], crs="EPSG:25833")

            # Create GeoDataFrame with WGS84 CRS
            transport_gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")

            # Transform to target CRS (EPSG:25833)
            transport_gdf = transport_gdf.to_crs("EPSG:25833")

            # Ensure district boundary has same CRS for spatial operations
            district_boundary_normalized = district_boundary.copy()
            if district_boundary_normalized.crs != "EPSG:25833":
                district_boundary_normalized = district_boundary_normalized.to_crs("EPSG:25833")

            # Clip transport stops to exact district boundary
            try:
                clipped_stops = gpd.clip(transport_gdf, district_boundary_normalized)
            except Exception as e:
                logger.warning(f"Clipping failed, using bbox-filtered results: {str(e)}")
                clipped_stops = transport_gdf

            logger.info(
                f"Successfully fetched {len(clipped_stops)} transport stops "
                f"(from {len(transport_gdf)} in bbox)"
            )

            return clipped_stops

        except Exception as e:
            error_msg = f"Failed to fetch transport stops from Overpass API: {str(e)}"
            logger.error(error_msg)
            raise

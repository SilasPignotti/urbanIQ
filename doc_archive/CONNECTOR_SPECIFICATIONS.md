# Connector Specifications

This document provides detailed implementation specifications for the data connectors used in urbanIQ.

## Berlin Geoportal WFS Connector

### Authentication

- **Type**: None required (public service)
- **Rate Limits**: No explicit limits documented
- **User-Agent**: Recommended to include project identification

### Common Parameters

```python
BASE_PARAMS = {
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "OUTPUTFORMAT": "application/json",
    "SRSNAME": "EPSG:25833"  # Target CRS
}
```

### District Boundaries (Bezirksgrenzen)

**Endpoint**: `https://gdi.berlin.de/services/wfs/alkis_bezirke`

**Layer Information**:

- **TypeName**: `alkis_bezirke:bezirke` (needs verification via DescribeFeatureType)
- **Geometry Type**: Polygon
- **Attributes**: bezname, schluessel, flaeche_ha (to be confirmed)

**Sample Implementation**:

```python
async def fetch_district_boundary(bezirk_name: str) -> gpd.GeoDataFrame:
    params = {
        **BASE_PARAMS,
        "TYPENAME": "alkis_bezirke:bezirke",
        "CQL_FILTER": f"bezname='{bezirk_name}'"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gdi.berlin.de/services/wfs/alkis_bezirke",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()

        gdf = gpd.read_file(StringIO(response.text))
        return gdf
```

**Error Handling**:

- HTTP 400: Invalid parameter (check bezirk name spelling)
- HTTP 500: Service unavailable
- Empty response: District name not found

### Buildings (Gebäude)

**Endpoint**: `https://gdi.berlin.de/services/wfs/alkis_gebaeude`

**Layer Information**:

- **TypeName**: `alkis_gebaeude:gebaeude` (needs verification)
- **Geometry Type**: Polygon
- **Attributes**: nutzung, geschosse, baujahr, flaeche_m2 (to be confirmed)

**Spatial Filtering**:

```python
async def fetch_buildings(district_boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Get bounding box from district
    bounds = district_boundary.total_bounds
    bbox_str = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]},EPSG:25833"

    params = {
        **BASE_PARAMS,
        "TYPENAME": "alkis_gebaeude:gebaeude",
        "BBOX": bbox_str
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gdi.berlin.de/services/wfs/alkis_gebaeude",
            params=params,
            timeout=60.0  # Buildings can be large datasets
        )
        response.raise_for_status()

        gdf = gpd.read_file(StringIO(response.text))

        # Clip to exact district boundary
        gdf_clipped = gpd.clip(gdf, district_boundary)
        return gdf_clipped
```

**Performance Considerations**:

- Large datasets: Consider pagination if available
- Timeout: Buildings queries can take 60+ seconds
- Memory: Process in chunks for large districts

## OpenStreetMap Overpass Connector

### Authentication

- **Type**: None required
- **Rate Limits**: Max 2 requests per second
- **Timeout**: 25 seconds (configurable in query)

### Public Transport Stops (ÖPNV Haltestellen)

**Endpoint**: `https://overpass-api.de/api/interpreter`

**Query Template**:

```overpass
[out:json][timeout:25];
(
  node["public_transport"="stop_position"]({{bbox}});
  node["highway"="bus_stop"]({{bbox}});
  node["railway"="tram_stop"]({{bbox}});
  node["amenity"="ferry_terminal"]({{bbox}});
);
out geom;
```

**Implementation**:

```python
async def fetch_transport_stops(district_boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Convert district boundary to WGS84 for OSM query
    district_wgs84 = district_boundary.to_crs("EPSG:4326")
    bounds = district_wgs84.total_bounds

    # Overpass bbox format: south,west,north,east
    bbox_str = f"{bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]}"

    query = f"""
    [out:json][timeout:25];
    (
      node["public_transport"="stop_position"]({bbox_str});
      node["highway"="bus_stop"]({bbox_str});
      node["railway"="tram_stop"]({bbox_str});
      node["amenity"="ferry_terminal"]({bbox_str});
    );
    out geom;
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers={"Content-Type": "text/plain"},
            timeout=30.0
        )
        response.raise_for_status()

        # Parse Overpass JSON response
        data = response.json()

        # Convert to GeoDataFrame
        features = []
        for element in data.get("elements", []):
            if element.get("lat") and element.get("lon"):
                point = Point(element["lon"], element["lat"])
                features.append({
                    "geometry": point,
                    "osm_id": element.get("id"),
                    "name": element.get("tags", {}).get("name", ""),
                    "operator": element.get("tags", {}).get("operator", ""),
                    "transport_mode": element.get("tags", {}).get("public_transport", ""),
                    **element.get("tags", {})
                })

        gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")

        # Transform to target CRS
        gdf = gdf.to_crs("EPSG:25833")

        return gdf
```

**Rate Limiting Implementation**:

```python
import asyncio
from datetime import datetime, timedelta

class OverpassRateLimiter:
    def __init__(self, max_requests_per_second: float = 2.0):
        self.max_requests_per_second = max_requests_per_second
        self.last_request_time = None

    async def acquire(self):
        if self.last_request_time:
            elapsed = datetime.now() - self.last_request_time
            min_interval = timedelta(seconds=1.0 / self.max_requests_per_second)

            if elapsed < min_interval:
                sleep_time = (min_interval - elapsed).total_seconds()
                await asyncio.sleep(sleep_time)

        self.last_request_time = datetime.now()
```

## Error Handling Strategy

### Common Error Patterns

**HTTP Errors**:

```python
class ConnectorError(Exception):
    pass

class ServiceUnavailableError(ConnectorError):
    pass

class InvalidParameterError(ConnectorError):
    pass

class RateLimitError(ConnectorError):
    pass

async def handle_http_errors(response):
    if response.status_code == 400:
        raise InvalidParameterError(f"Bad request: {response.text}")
    elif response.status_code == 429:
        raise RateLimitError("Rate limit exceeded")
    elif response.status_code >= 500:
        raise ServiceUnavailableError(f"Service error: {response.status_code}")

    response.raise_for_status()
```

**Retry Strategy**:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def fetch_with_retry(url: str, **kwargs):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, **kwargs)
        await handle_http_errors(response)
        return response
```

## Testing and Validation

### Layer Name Discovery

Before implementation, verify the exact layer names:

```bash
# Get capabilities for bezirke
curl "https://gdi.berlin.de/services/wfs/alkis_bezirke?SERVICE=WFS&REQUEST=GetCapabilities"

# Get feature type details
curl "https://gdi.berlin.de/services/wfs/alkis_bezirke?SERVICE=WFS&REQUEST=DescribeFeatureType"

# Test single feature
curl "https://gdi.berlin.de/services/wfs/alkis_bezirke?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAME=[layer_name]&COUNT=1"
```

### Validation Checklist

- [ ] Verify exact layer names via DescribeFeatureType
- [ ] Test coordinate system transformation
- [ ] Validate attribute names and types
- [ ] Test spatial filtering accuracy
- [ ] Confirm licensing and attribution requirements
- [ ] Test error handling for invalid inputs
- [ ] Validate performance with large datasets

## Performance Benchmarks

**Expected Response Times** (to be measured):

- District boundaries: < 2 seconds
- Buildings (per district): 15-60 seconds
- Transport stops: < 10 seconds

**Memory Usage** (estimated):

- District boundary: < 1 MB
- Buildings: 10-100 MB per district
- Transport stops: < 5 MB per district

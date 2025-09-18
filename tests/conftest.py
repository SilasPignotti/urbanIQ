"""
Core test fixtures and infrastructure for urbanIQ testing suite.

Provides database fixtures, FastAPI TestClient setup, mock external services,
and sample geodata for comprehensive testing of all application components.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point, Polygon
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.models import DataSource, Job, JobStatus, Package
from app.models.data_source import ConnectorType


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine with temporary SQLite file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        database_url = f"sqlite:///{tmp_file.name}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)
        yield engine
        # Cleanup
        Path(tmp_file.name).unlink(missing_ok=True)


@pytest.fixture
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create test database session with automatic rollback."""
    with Session(test_db_engine) as session:
        yield session
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with test database dependency override."""

    def get_test_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_job(db_session: Session) -> Job:
    """Create sample job record for testing."""
    job = Job(
        id="test-job-123",
        user_request="Pankow Gebäude und ÖPNV-Haltestellen für Mobilitätsanalyse",
        bezirk="Pankow",
        datasets=["gebaeude", "oepnv_haltestellen"],
        status=JobStatus.PENDING,
        progress=0,
        error_message=None,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def completed_job(db_session: Session) -> Job:
    """Create completed job record with package for testing."""
    job = Job(
        id="completed-job-456",
        user_request="Charlottenburg buildings analysis",
        bezirk="Charlottenburg-Wilmersdorf",
        datasets=["gebaeude"],
        status=JobStatus.COMPLETED,
        progress=100,
        error_message=None,
    )
    db_session.add(job)
    db_session.commit()

    # Create associated package
    package = Package(
        id="package-456",
        job_id=job.id,
        file_path="/tmp/test_package.zip",
        file_size=1024,
        metadata_report="Test metadata report",
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def sample_package(db_session: Session) -> Package:
    """Create sample package record for testing."""
    package = Package(
        id="test-package-789",
        job_id="test-job-789",
        file_path="/tmp/test_geodata_package.zip",
        file_size=2048,
        metadata_report="Comprehensive metadata report for test package",
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)
    return package


@pytest.fixture
def sample_data_sources(db_session: Session) -> list[DataSource]:
    """Create sample data source records for testing."""
    sources = [
        DataSource(
            id="berlin-geoportal",
            name="Berlin Geoportal WFS",
            connector_type=ConnectorType.GEOPORTAL,
            service_url="https://fbinter.stadt-berlin.de/fb/wfs/geometry/senstadt/re_gebaeude",
            description="Berlin building geometries from official WFS service",
            active=True,
        ),
        DataSource(
            id="openstreetmap",
            name="OpenStreetMap Overpass API",
            connector_type=ConnectorType.OSM,
            service_url="https://overpass-api.de/api/interpreter",
            description="OpenStreetMap public transport stops via Overpass API",
            active=True,
        ),
    ]
    for source in sources:
        db_session.add(source)
    db_session.commit()
    for source in sources:
        db_session.refresh(source)
    return sources


@pytest.fixture
def sample_berlin_geodata() -> gpd.GeoDataFrame:
    """Create sample Berlin geodata for testing."""
    # Create realistic Berlin coordinates (Pankow district area)
    berlin_points = [
        Point(13.4014, 52.5691),  # Pankow center
        Point(13.4194, 52.5581),  # Near S-Bahn station
        Point(13.3894, 52.5801),  # Northern Pankow
        Point(13.4294, 52.5491),  # Eastern Pankow
    ]

    data = {
        "feature_id": ["building_001", "building_002", "stop_001", "stop_002"],
        "dataset_type": ["gebaeude", "gebaeude", "oepnv_haltestellen", "oepnv_haltestellen"],
        "source_system": ["berlin_geoportal", "berlin_geoportal", "openstreetmap", "openstreetmap"],
        "bezirk": ["Pankow", "Pankow", "Pankow", "Pankow"],
        "geometry": berlin_points,
        "original_attributes": [
            {"height": 15.5, "type": "residential"},
            {"height": 23.2, "type": "commercial"},
            {"name": "S Pankow", "transport_type": "s_bahn"},
            {"name": "Pankow Kirche", "transport_type": "bus"},
        ],
    }

    return gpd.GeoDataFrame(data, crs="EPSG:25833")


@pytest.fixture
def pankow_district_boundary() -> gpd.GeoDataFrame:
    """Create sample Pankow district boundary for testing."""
    # Simplified Pankow boundary polygon
    pankow_coords = [
        (13.380, 52.540),
        (13.450, 52.540),
        (13.450, 52.600),
        (13.380, 52.600),
        (13.380, 52.540),
    ]

    boundary = Polygon(pankow_coords)

    data = {
        "bezirk_name": ["Pankow"],
        "bezirk_id": ["03"],
        "area_km2": [103.07],
        "geometry": [boundary],
    }

    return gpd.GeoDataFrame(data, crs="EPSG:4326")


@pytest.fixture
def mock_gemini_response():
    """Mock Google Gemini API response for NLP parsing."""
    return {
        "bezirk": "Pankow",
        "datasets": ["gebaeude", "oepnv_haltestellen"],
        "confidence": 0.95,
        "reasoning": "Clear request for buildings and transport stops in Pankow district",
    }


@pytest.fixture
def mock_wfs_response():
    """Mock Berlin Geoportal WFS response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:gml="http://www.opengis.net/gml/3.2">
    <wfs:member>
        <app:feature>
            <app:geometry>
                <gml:Point srsName="EPSG:25833">
                    <gml:coordinates>383000,5820000</gml:coordinates>
                </gml:Point>
            </app:geometry>
            <app:height>15.5</app:height>
            <app:type>residential</app:type>
        </app:feature>
    </wfs:member>
</wfs:FeatureCollection>"""


@pytest.fixture
def mock_osm_response():
    """Mock OpenStreetMap Overpass API response."""
    return {
        "version": 0.6,
        "generator": "Overpass API",
        "elements": [
            {
                "type": "node",
                "id": 123456789,
                "lat": 52.5691,
                "lon": 13.4014,
                "tags": {
                    "name": "S Pankow",
                    "public_transport": "platform",
                    "railway": "platform",
                    "transport": "s_bahn",
                },
            },
            {
                "type": "node",
                "id": 987654321,
                "lat": 52.5581,
                "lon": 13.4194,
                "tags": {"name": "Pankow Kirche", "highway": "bus_stop", "transport": "bus"},
            },
        ],
    }


@pytest.fixture
def mock_external_services():
    """Mock all external service dependencies for isolated testing."""
    with (
        patch("app.services.nlp_service.ChatOpenAI") as mock_openai,
        patch("httpx.AsyncClient.get") as mock_http_get,
        patch("httpx.AsyncClient.post") as mock_http_post,
    ):
        # Configure mock OpenAI response
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = Mock(
            content='{"bezirk": "Pankow", "datasets": ["gebaeude"], "confidence": 0.95}'
        )
        mock_openai.return_value = mock_llm_instance

        # Configure mock HTTP responses
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0"?>
        <wfs:FeatureCollection>
            <wfs:member><app:feature><app:geometry>
                <gml:Point><gml:coordinates>13.4,52.5</gml:coordinates></gml:Point>
            </app:geometry></app:feature></wfs:member>
        </wfs:FeatureCollection>"""
        mock_response.json.return_value = {
            "elements": [{"type": "node", "lat": 52.5, "lon": 13.4, "tags": {}}]
        }

        mock_http_get.return_value = mock_response
        mock_http_post.return_value = mock_response

        yield {
            "openai": mock_openai,
            "http_get": mock_http_get,
            "http_post": mock_http_post,
        }


@pytest.fixture
def temp_export_dir() -> Generator[Path, None, None]:
    """Create temporary directory for export testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "exports"
        export_path.mkdir(exist_ok=True)
        yield export_path


@pytest.fixture
def temp_zip_file(temp_export_dir: Path) -> Path:
    """Create temporary ZIP file for download testing."""
    zip_path = temp_export_dir / "test_package.zip"
    # Create a minimal ZIP file
    import zipfile

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("README.md", "Test geodata package")
        zf.writestr("data.geojson", '{"type": "FeatureCollection", "features": []}')
    return zip_path


# Performance testing fixtures
@pytest.fixture(scope="session")
def performance_test_config():
    """Configuration for performance testing."""
    return {
        "max_concurrent_requests": 10,
        "max_response_time_seconds": 30,
        "max_memory_usage_mb": 512,
    }


# German language test cases
@pytest.fixture
def german_test_requests():
    """Sample German language requests for NLP testing."""
    return [
        "Pankow Gebäude und ÖPNV-Haltestellen für Mobilitätsanalyse",
        "Charlottenburg Wohngebäude für Stadtplanung",
        "Mitte buildings and transport infrastructure",
        "Friedrichshain Verkehrsinfrastruktur",
        "Kreuzberg öffentliche Verkehrsmittel",
    ]


@pytest.fixture
def invalid_test_requests():
    """Invalid requests for error testing."""
    return [
        "",  # Empty request
        "x",  # Too short
        "a" * 501,  # Too long
        "Unclear request without location",  # Low confidence
        "Hamburg buildings",  # Wrong city
    ]

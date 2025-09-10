# Database Schema

This document defines the complete database schema for urbanIQ Berlin geodata aggregation system.

## Job Management

### jobs Table

Manages asynchronous geodata processing jobs initiated by user requests.

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    request_text TEXT NOT NULL,
    bezirk TEXT,
    categories TEXT,  -- JSON Array: ["transport", "environment"]
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    result_package_id TEXT,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);
```

**Fields:**

- `id`: Unique job identifier (UUID)
- `status`: Current processing status (pending → processing → completed/failed)
- `request_text`: Original user request in natural language
- `bezirk`: Extracted Berlin district name
- `categories`: JSON array of requested data categories
- `progress`: Processing progress percentage (0-100)
- `result_package_id`: Reference to generated package (when completed)
- `error_message`: Error details (when failed)
- `created_at`/`completed_at`: Timestamps for job lifecycle

## Package Management

### packages Table

Manages downloadable ZIP packages containing geodata and metadata reports.

```sql
CREATE TABLE packages (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    file_path TEXT NOT NULL,
    file_size INTEGER,
    download_count INTEGER DEFAULT 0,
    metadata_report TEXT,  -- LLM-generierter Metadaten-Report
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME DEFAULT (datetime(CURRENT_TIMESTAMP, '+24 hours'))
);
```

**Fields:**

- `id`: Unique package identifier
- `job_id`: Reference to originating job
- `file_path`: Local filesystem path to ZIP package
- `file_size`: Package size in bytes
- `download_count`: Number of times package was downloaded
- `metadata_report`: LLM-generated markdown metadata report
- `created_at`: Package creation timestamp
- `expires_at`: Automatic cleanup timestamp (24h default)

## Data Source Registry

### data_sources Table

Registry of available geodata sources with curated metadata.

```sql
CREATE TABLE data_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    connector_type TEXT NOT NULL CHECK (connector_type IN ('geoportal', 'osm')),
    service_url TEXT NOT NULL,
    layer_name TEXT,
    category TEXT NOT NULL,
    subcategory TEXT,
    metadata_json TEXT NOT NULL,  -- Kuratierte Metadaten
    active BOOLEAN DEFAULT TRUE,
    last_tested DATETIME,
    test_status TEXT CHECK (test_status IN ('ok', 'error', 'timeout'))
);
```

**Fields:**

- `id`: Unique source identifier
- `name`: Human-readable source name
- `description`: Source description for metadata reports
- `connector_type`: Connection method ('geoportal' for WFS, 'osm' for Overpass API)
- `service_url`: Base URL for data access
- `layer_name`: Specific layer/dataset identifier
- `category`: Primary data category (transport, environment, administrative, etc.)
- `subcategory`: Refined categorization
- `metadata_json`: Curated metadata (license, quality, update frequency)
- `active`: Whether source is currently available
- `last_tested`/`test_status`: Health check information

## Available Categories

The system supports the following data categories:

- **administrative**: District boundaries, administrative areas
- **transport**: Streets, public transport, cycling infrastructure
- **environment**: Parks, water bodies, environmental monitoring
- **social_infrastructure**: Schools, hospitals, cultural facilities
- **demographics**: Population data, census information
- **urban_planning**: Zoning, building permits, development areas

## Database Configuration

- **Engine**: SQLite (development/MVP phase)
- **ORM**: SQLModel (SQLAlchemy + Pydantic integration)
- **Migration Strategy**: Alembic for schema evolution
- **Connection Pool**: Single connection for SQLite, configurable for PostgreSQL migration

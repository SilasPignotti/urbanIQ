# Implementation Roadmap

This document provides a structured implementation plan for urbanIQ, broken down into manageable PRPs (Project Requirements Processes) that can be executed sequentially.

## 🏗️ Implementation Strategy

The implementation is divided into 6 phases with 14 distinct steps, each designed as a self-contained PRP that builds upon previous work. The roadmap follows dependency chains to ensure smooth development flow.

## Phase 1: Foundation & Core Services

### Schritt 1: Projekt-Setup und Basis-Struktur

**Claude Code Message:**

```
Erstelle ein PRP für "Projekt-Setup und Basis-Struktur": FastAPI App initialisieren mit main.py, Grundkonfiguration mit Settings, strukturiertes Logging Setup, Health Check Endpoint, Dependency Injection Container, Environment Variable Management, und CORS Konfiguration. Basis-Struktur für app/api/, app/services/, app/models/ erstellen.
```

**Deliverables:**

- FastAPI application setup with main.py
- Pydantic Settings configuration
- Structured logging with JSON output
- Health check endpoint (/health)
- Dependency injection container
- Environment variable management
- CORS configuration

**Dependencies:** None (Foundation step)

### Schritt 2: Database Models und Schema

**Claude Code Message:**

```
Erstelle ein PRP für "Database Models und SQLModel Setup": SQLModel Klassen für jobs, packages, data_sources Tabellen implementieren entsprechend DATABASE_SCHEMA.md, Alembic Migrationen erstellen, Database Session Management mit SQLModel, Connection Pooling Setup, und Database Initialization Scripts.
```

**Deliverables:**

- SQLModel classes for jobs, packages, data_sources tables
- Alembic migration setup and initial migrations
- Database session management
- Connection pooling configuration
- Database initialization scripts
- SQLite configuration for development

**Dependencies:** Schritt 1 (requires basic app structure)

### Schritt 3: NLP Service (Gemini Integration)

**Claude Code Message:**

```
Erstelle ein PRP für "NLP Service - Gemini Integration": LangChain Google GenAI Integration implementieren, parse_user_request Funktion für Bezirk und Dataset Extraktion aus natürlicher Sprache, Structured Output Parsing mit Pydantic Models, Confidence Threshold Handling, und Error Handling für niedrige Confidence Scores.
```

**Deliverables:**

- LangChain Google GenAI integration
- parse_user_request function implementation
- Structured output parsing with Pydantic models
- Confidence threshold validation (>= 0.7)
- Error handling for low confidence scores
- Berlin district name validation
- Dataset type extraction (gebaeude, oepnv_haltestellen)

**Dependencies:** Schritt 1 (requires app structure and configuration)

## Phase 2: Data Connectors

### Schritt 4: Berlin Geoportal WFS Connector

**Claude Code Message:**

```
Erstelle ein PRP für "Berlin Geoportal WFS Connector": HTTP Client für Berlin Geoportal WFS Services implementieren, Bezirksgrenzen und Gebäude Connector Klassen, Retry Logic mit exponential backoff, Spatial Filtering mit BBOX, CRS Handling EPSG:25833, Error Handling für WFS Responses, und GeoDataFrame Integration.
```

**Deliverables:**

- WFS client for Berlin Geoportal services
- District boundaries connector (alkis_bezirke)
- Buildings connector (alkis_gebaeude)
- HTTP client with retry logic and exponential backoff
- Spatial filtering with BBOX parameters
- CRS handling for EPSG:25833
- Error handling for WFS service responses
- GeoDataFrame integration and validation

**Dependencies:** Schritt 1 (requires app structure)

### Schritt 5: OpenStreetMap Overpass Connector

**Claude Code Message:**

```
Erstelle ein PRP für "OpenStreetMap Overpass Connector": Overpass API Client für ÖPNV-Haltestellen implementieren, Rate Limiting (2 req/sec), Overpass Query Templates für public_transport stops, CRS Transformation WGS84→ETRS89/UTM33N, JSON Response zu GeoDataFrame Konvertierung, und Timeout Handling.
```

**Deliverables:**

- Overpass API client implementation
- Rate limiting (max 2 requests per second)
- Query templates for public transport stops
- CRS transformation WGS84 → ETRS89/UTM33N
- JSON response to GeoDataFrame conversion
- Timeout handling (25 seconds)
- OSM tag processing and attribute mapping

**Dependencies:** Schritt 1 (requires app structure)

### Schritt 6: Data Service Orchestration

**Claude Code Message:**

```
Erstelle ein PRP für "Data Service - Connector Orchestration": fetch_datasets_for_request Funktion implementieren, Parallel Processing mit asyncio.gather für alle Connectors, automatisches District Boundary Loading, Error Resilience für partial failures, Runtime Statistics Collection, und Service Health Monitoring.
```

**Deliverables:**

- fetch_datasets_for_request function implementation
- Parallel processing with asyncio.gather
- Automatic district boundary loading for all requests
- Error resilience for partial connector failures
- Runtime statistics collection
- Service health monitoring
- Data source registry integration

**Dependencies:** Schritte 4, 5 (requires both connectors)

## Phase 3: Processing & Metadata

### Schritt 7: Processing Service (Data Harmonization)

**Claude Code Message:**

```
Erstelle ein PRP für "Processing Service - Data Harmonization": harmonize_datasets Funktion implementieren, CRS Standardization zu EPSG:25833, Spatial Clipping zu District Boundaries, Schema Standardization mit einheitlichen Attributen, Geometry Validation, und Quality Assurance Checks für alle GeoDataFrames.
```

**Deliverables:**

- harmonize_datasets function implementation
- CRS standardization to EPSG:25833
- Spatial clipping to district boundaries
- Schema standardization with unified attributes
- Geometry validation and cleaning
- Quality assurance checks
- Feature count and coverage statistics

**Dependencies:** Schritt 6 (requires data service orchestration)

### Schritt 8: LLM Metadata Service

**Claude Code Message:**

```
Create a PRP for "LLM Metadata Service - Report Generation": implement create_metadata_report function with Gemini integration, Markdown report templates for geodata metadata reports, dataset analysis and quality assessment, context preparation for LLM processing, and usage recommendations generation.
```

**Deliverables:**

- create_metadata_report function with Gemini integration
- Markdown report templates for geodata metadata
- Dataset analysis and quality assessment
- Context preparation for LLM processing
- Usage recommendations generation
- Legal information and licensing details

**Dependencies:** Schritt 3 (requires NLP service for LLM integration)

## Phase 4: API Layer

### Schritt 9: Core API Endpoints

**Claude Code Message:**

```
just Create a PRP for "Core API Endpoints": implement POST /api/chat/message for Chat Interface, GET /api/jobs/status/{job_id} for Job Status, Job Management with Database Integration, Pydantic Request/Response Models, Input Validation, and Error Response Handling according to API_DESIGN.md.
```

**Deliverables:**

- POST /api/chat/message endpoint
- GET /api/jobs/status/{job_id} endpoint
- Job management with database integration
- Pydantic request/response models
- Input validation and sanitization
- Error response handling
- OpenAPI documentation integration

**Dependencies:** Schritte 2, 3 (requires database models and NLP service)

### Schritt 10: Background Job Processing

**Claude Code Message:**

```
Create a PRP for "Background Job Processing System": implement Async Job Queue System, Service Integration Pipeline (NLP→Data→Processing→Metadata), Progress Tracking with Database Updates, ZIP Package Generation with GeoData and Reports, and Job Status Management (pending→processing→completed).
```

**Deliverables:**

- Async job queue system
- Service integration pipeline (NLP → Data → Processing → Metadata)
- Progress tracking with database updates
- ZIP package generation with geodata and reports
- Job status management (pending → processing → completed)
- Error handling and recovery mechanisms

**Dependencies:** Schritte 6, 7, 8, 9 (requires all services and API endpoints)

## Phase 5: Frontend & File Handling

### Schritt 11: Package Management & Download

**Claude Code Message:**

```
Create a PRP for "Package Management and Download System": ZIP Package Creation with GeoData Files and Metadata Reports, File Storage Management in data/exports/ directory, Download Endpoints with File Serving, Automatic Cleanup Jobs for expired packages, and Package Metadata Database Storage.
```

**Deliverables:**

- ZIP package creation with geodata files and metadata reports
- File storage management in data/exports/ directory
- Download endpoints with secure file serving
- Automatic cleanup jobs for expired packages
- Package metadata database storage
- Download tracking and statistics

**Dependencies:** Schritt 10 (requires job processing system)

### Schritt 12: Frontend Implementation

**Claude Code Message:**

```
Create a PRP for "HTMX Frontend Implementation": Jinja2 Templates for Chat Interface, HTMX Integration for reactive UI updates, Progress Indicators for Job Status, Download UI for ZIP Packages, Tailwind CSS Styling, and Static Files Setup according to FRONTEND_IMPLEMENTATION.md.
```

**Deliverables:**

- Jinja2 templates for chat interface
- HTMX integration for reactive UI updates
- Progress indicators for job status
- Download UI for ZIP packages
- Tailwind CSS styling and responsive design
- Static files setup and serving
- Accessibility features

**Dependencies:** Schritte 9, 11 (requires API endpoints and package management)

## Phase 6: Testing & Deployment

### Schritt 13: Comprehensive Testing

**Claude Code Message:**

```
Create a PRP for "Testing Suite Implementation": implement Unit Tests for all Services, Integration Tests for API Endpoints, Mock Connectors for Testing, Test Database Setup, Pytest Configuration with Coverage, and Test Data Generation according to TESTING_STRATEGY.md.
```

**Deliverables:**

- Unit tests for all services
- Integration tests for API endpoints
- Mock connectors for isolated testing
- Test database setup and fixtures
- Pytest configuration with coverage reporting
- Test data generation utilities
- Continuous integration test setup

**Dependencies:** All previous steps (comprehensive testing of complete system)

### Schritt 14: Production Ready Features

**Claude Code Message:**

```
Create a PRP for "Production Features": Environment Configuration for Development/Production, Docker Setup with multi-stage builds, Comprehensive Health Checks for all Services, Structured Logging with Correlation IDs, Security Headers, and Production-ready CORS Configuration according to DEPLOYMENT_CONFIGURATION.md.
```

**Deliverables:**

- Environment configuration for development/production
- Docker setup with multi-stage builds
- Comprehensive health checks for all services
- Structured logging with correlation IDs
- Security headers and middleware
- Production-ready CORS configuration
- Performance monitoring and metrics
- Deployment documentation

**Dependencies:** All previous steps (production deployment of complete system)

### Schritt 15: Comprehensive Test Suite Implementation

**Claude Code Message:**

```
Implement comprehensive test suite for production readiness: Complete unit tests for all API endpoints, Integration tests for service interactions, End-to-end workflow tests, Performance testing suite, Error handling and edge case coverage, Test data generators for realistic scenarios, CI/CD pipeline optimization for full test coverage, and Mock service implementations for external dependencies.
```

**Deliverables:**

- Complete unit test coverage for all API endpoints
- Integration tests for service-to-service interactions
- End-to-end workflow tests for complete user journeys
- Performance testing suite with benchmarks
- Comprehensive error handling and edge case tests
- Test data generators for realistic testing scenarios
- Mock implementations for external services (Geoportal, OSM)
- Optimized CI/CD pipeline with full test coverage
- Test documentation and maintenance guidelines
- Automated test reporting and metrics

**Dependencies:** Schritt 14 (requires production-ready system for comprehensive testing)

**Note:** This step was deferred from earlier implementation phases to focus on MVP delivery. Essential tests (models, core services) remain in simplified CI pipeline for rapid development cycles.

## 📅 Recommended Timeline

### Week 1: Foundation (Schritte 1-3)

- Day 1-2: Project setup and basic structure
- Day 3-4: Database models and schema
- Day 5: NLP service implementation

### Week 2: Data Layer (Schritte 4-6)

- Day 1-2: Berlin Geoportal WFS connector
- Day 3-4: OpenStreetMap Overpass connector
- Day 5: Data service orchestration

### Week 3: Processing (Schritte 7-8)

- Day 1-3: Processing service and data harmonization
- Day 4-5: LLM metadata service

### Week 4: API & Frontend (Schritte 9-12)

- Day 1-2: Core API endpoints
- Day 3: Background job processing
- Day 4: Package management and download
- Day 5: Frontend implementation

### Week 5: Finalization (Schritte 13-14)

- Day 1-3: Comprehensive testing
- Day 4-5: Production ready features

## 🔗 Critical Dependencies

### Sequential Dependencies (Must be completed in order):

1. **Schritt 1** → All other steps (foundation requirement)
2. **Schritt 2** → Schritte 9, 10, 11 (database models required)
3. **Schritt 4** → Schritt 6 (district boundaries needed for all processing)
4. **Schritt 6** → Schritt 7 (data service needed for processing)
5. **Schritt 9** → Schritt 10 (API endpoints needed for job processing)
6. **Schritt 10** → Schritt 11 (job processing needed for package management)

### Parallel Development Opportunities:

- Schritte 4 & 5 (both connectors can be developed simultaneously)
- Schritte 7 & 8 (processing and metadata services are independent)
- Schritte 11 & 12 (package management and frontend can be developed in parallel)

## 🚀 Getting Started

To begin implementation:

1. **Start with Foundation**: Execute Schritt 1 using the provided Claude Code message
2. **Follow Dependencies**: Complete each step's dependencies before moving forward
3. **Test Incrementally**: Test each component as it's completed
4. **Document Progress**: Update this roadmap with actual completion dates and notes

## 📋 Success Criteria

Each step should be considered complete when:

- All deliverables are implemented and tested
- Code follows established patterns and conventions
- Documentation is updated accordingly
- Dependencies for subsequent steps are satisfied
- Integration with existing components is verified

## 🔧 Development Notes

### Environment Setup

- Python 3.11+ with UV package manager
- GDAL libraries for geospatial processing
- Google Gemini API key for LLM integration
- Docker for containerization (later phases)

### Key Libraries

- FastAPI for web framework
- SQLModel for database ORM
- GeoPandas for geospatial data processing
- LangChain for LLM integration
- HTMX for frontend reactivity
- Tailwind CSS for styling

### Quality Assurance

- Type hints throughout codebase
- Comprehensive error handling
- Structured logging with correlation IDs
- Unit and integration testing
- Performance monitoring and optimization

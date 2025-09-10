# Service Architecture

This document defines the core service architecture for urbanIQ Berlin geodata aggregation system.

## Architecture Overview

The system follows a service-oriented architecture with four core services that orchestrate geodata acquisition, processing, and metadata generation.

## 1. NLP Service (Gemini Integration)

**Purpose**: Parse natural language user requests to extract Berlin districts and data categories.

**Technology Stack**:

- LangChain Google GenAI integration
- Google Gemini 1.5 Pro model
- Temperature: 0.1 (deterministic parsing)

**Key Methods**:

### parse_user_request(text: str) → Dict[str, any]

Extracts structured information from natural language input.

**Input**: "Pankow Verkehrsdaten für Mobilitätsanalyse"
**Output**:

```json
{
  "bezirk": "Pankow",
  "categories": ["transport"],
  "confidence": 0.95
}
```

**Available Berlin Districts**:

- Mitte, Pankow, Charlottenburg-Wilmersdorf
- Spandau, Steglitz-Zehlendorf, Tempelhof-Schöneberg
- Neukölln, Treptow-Köpenick, Marzahn-Hellersdorf
- Lichtenberg, Reinickendorf, Friedrichshain-Kreuzberg

**Available Categories**:

- administrative, transport, environment
- social_infrastructure, demographics, urban_planning

**Error Handling**:

- Confidence threshold: 0.7
- Fallback for ambiguous requests
- Suggestion generation for unclear input

## 2. Data Service (Connector Orchestration)

**Purpose**: Coordinate geodata acquisition from multiple external sources.

**Key Methods**:

### fetch_datasets_for_request(bezirk: str, categories: List[str]) → List[Dict]

Orchestrates parallel data acquisition from all relevant sources.

**Process Flow**:

1. Query data source registry for relevant datasets
2. Load district boundary for spatial filtering
3. Execute parallel connector requests
4. Filter successful results and handle errors
5. Calculate runtime statistics

**Output Structure**:

```python
{
    "dataset_id": "bezirksgrenzen_berlin",
    "geodata": GeoDataFrame,
    "predefined_metadata": Dict,
    "runtime_stats": {
        "feature_count": 1500,
        "spatial_extent": [13.0, 52.3, 13.8, 52.7],
        "coverage_percentage": 95.0,
        "data_quality_score": 0.85
    }
}
```

**Error Resilience**:

- Timeout handling per connector
- Partial success scenarios
- Quality score calculation
- Coverage assessment

## 3. Processing Service (Data Harmonization)

**Purpose**: Standardize and combine geodata from multiple sources.

**Target CRS**: ETRS89/UTM33N (EPSG:25833) - Standard for Berlin

**Key Methods**:

### harmonize_datasets(datasets: List[Dict], target_boundary: GeoDataFrame) → GeoDataFrame

Harmonizes multiple geodatasets into unified format.

**Processing Steps**:

1. **CRS Standardization**: Transform all datasets to EPSG:25833
2. **Spatial Clipping**: Clip to target district boundary
3. **Schema Standardization**: Apply common attribute schema
4. **Data Combination**: Merge all datasets into single GeoDataFrame

**Standard Schema**:

```python
{
    "feature_id": "unique_identifier",
    "dataset_source": "source_dataset_id",
    "category": "transport|environment|administrative",
    "geometry": "standardized_geometry_column"
}
```

**Quality Assurance**:

- Geometry validation
- Attribute completeness checks
- Spatial relationship verification
- Empty geometry handling

## 4. LLM Metadata Service

**Purpose**: Generate professional metadata reports using Gemini analysis.

**Key Methods**:

### create_metadata_report(datasets: List[Dict], bezirk: str, request_info: Dict) → str

Creates comprehensive metadata reports for geodata packages.

**Report Structure**:

```markdown
# Geodaten-Metadatenreport: [Bezirk]

## Übersicht

- Erstellungsdatum, Bezirk, Anzahl Datensätze
- Koordinatensystem: ETRS89/UTM Zone 33N

## Enthaltene Datensätze

- Name, Beschreibung, Anbieter
- Aktualität, Nutzungslizenz
- Feature-Anzahl, Qualitätsbewertung

## Datenqualität und Vollständigkeit

- Gesamtbewertung, Lücken, Besonderheiten

## Nutzungsempfehlungen

- GIS-Software Hinweise
- Analyse-Empfehlungen

## Rechtliche Hinweise

- Lizenzbestimmungen
- Nutzungsrechte
```

**Context Preparation**:

- Dataset metadata aggregation
- Runtime statistics integration
- Usage note compilation
- Quality assessment summary

## Service Integration

**Dependency Injection**: FastAPI dependency system
**Async Coordination**: asyncio.gather for parallel processing
**Error Propagation**: Structured exception hierarchy
**Resource Management**: Connection pooling and cleanup

## Performance Considerations

**Parallel Processing**: All external API calls run concurrently
**Caching Strategy**: API response caching for repeated requests
**Resource Limits**: Timeout configuration per service
**Memory Management**: Streaming processing for large datasets

## Monitoring and Logging

**Service Health Checks**: Individual service status monitoring
**Performance Metrics**: Response time and success rate tracking
**Error Logging**: Structured logging with correlation IDs
**Usage Analytics**: Request pattern analysis for optimization

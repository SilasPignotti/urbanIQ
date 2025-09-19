# urbanIQ Berlin - Master's Course Presentation

## Geodatenhaltung und -vernetzung

---

**Präsentation für Master Geoinformation**  
**Kurs**: Geodatenhaltung und -vernetzung  
**Datum**: 19. September 2025  
**Student**: Silas Pignotti  
**Projekt**: urbanIQ Berlin MVP

---

## 📋 Überblick der Präsentation

1. **Allgemeine Projektidee & Use Cases**
2. **Reales Problem & Lösung**
3. **Systemarchitektur & Tech Stack**
4. **Geodatenhaltung & -vernetzung**
5. **Entwicklungszyklus & Tools**
6. **Live Demo**

## 💻 Codebase

https://github.com/SilasPignotti/urbanIQ

---

## 🏙️ 1. Allgemeine Projektidee & Use Cases

### Vision

**urbanIQ Berlin** = Intelligenter Geodaten-Aggregator für automatisierte Bezirksanalysen

### Kernidee

- **Natural Language Interface**: "Mobilitätsanalyse im Bezirk Pankow" -> ruft automatisch die dafür nötigen Datensätze ab
- **Automatisierte Datenverarbeitung**: Von Anfrage bis zur fertigen ZIP-Datei
- **Multi-Source Integration**: Berlin Geoportal WFS + OpenStreetMap
- **LLM-generierte Metadaten**: Professionelle Datenberichte

### Typische Use Cases

- **Stadtplaner**: "Charlottenburg Bezirksanalyse mit Gebäudedaten"
- **GIS-Analyst**: "Pankow Mobilitätsanalyse ÖPNV und Radwege"
- **Forscher**: "Mitte Demografische Analyse mit Bevölkerungsdichte"
- **Student**: "Friedrichshain Stadtentwicklung Gebäude und Infrastruktur"

---

## 🎯 2. Reales Problem & Lösung

### Das Problem

**Geodatensilos & Komplexe Beschaffung**

- 🔍 **Zeitaufwand**: Stunden für manuelle Datensuche & -beschaffung
- 🏢 **Verteilte Quellen**: Berlin Geoportal, OSM, verschiedene APIs
- 📊 **Inkonsistente Formate**: CRS-Chaos, Schema-Heterogenität
- 📝 **Manuelle Metadaten**: Dokumentation fehlt oder ist unvollständig
- 🧩 **Räumliche Filterung**: Manuelle Bezirks-Clipping erforderlich
- 🎓 **Technisches Know-how**: GIS-Expertise & Programmier-Kenntnisse erforderlich

### urbanIQ Lösung

**Automatisierte Geodaten-Pipeline**

- ⚡ **3-Minuten-Workflow**: Von Anfrage bis zum Download
- 🤖 **NLP-Interface**: Deutsche Sprache → Strukturierte Abfrage
- 🌐 **Multi-Source**: Automatische Datenquellen-Orchestrierung
- 📐 **Harmonisierung**: ETRS89/UTM33N Standard, einheitliche Schemas
- 📋 **KI-Metadaten**: Professionelle Reports mit Qualitätsbewertung
- 📦 **ZIP-Package**: GeoJSON + Shapefile + Metadaten + Lizenzinfo

---

## 🏗️ 3. Systemarchitektur & Tech Stack

### Service-Orientierte Architektur (4 Kernservices)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NLP Service   │    │  Data Service   │    │Processing Service│   │Metadata Service │
│   (OpenAI GPT)  │───▶│  (Orchestration)│───▶│ (Harmonization) │───▶│ (LLM Reports)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│German NL Query  │    │Multi-Connector  │    │CRS Transform    │    │Professional     │
│"Pankow Gebäude" │    │Berlin Geoportal │    │Spatial Clipping │    │Metadata Reports │
│Districts+Datasets│    │OpenStreetMap    │    │Schema Normal.   │    │Quality Scores   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tech Stack (Modern Python Ecosystem)

**Backend Foundation**

- **FastAPI**: Async REST API mit automatischer OpenAPI-Docs
- **SQLModel**: Type-safe ORM mit Pydantic Integration
- **SQLite**: Embedded Database für MVP Simplicität
- **Alembic**: Database Migration Management & Schema Versioning

**Geodaten-Stack**

- **GeoPandas**: Spatial DataFrames für Geodaten-Manipulation
- **Shapely**: Geometrische Operationen & Spatial Analytics
- **Fiona/GDAL**: Multi-Format Geodaten I/O (GeoJSON, Shapefile)

**KI-Integration**

- **LangChain**: LLM-Orchestrierung mit strukturierten Outputs
- **OpenAI GPT-4**: Natural Language Processing & Metadata Generation
- **Pydantic**: Type-sichere Datenvalidierung & Parsing
  **Frontend & Deployment**

- **HTMX**: Interactive Web UI ohne JavaScript Komplexität
- **Tailwind CSS**: Utility-first CSS für moderne UI
- **Docker**: Containerisierte Deployment-Pipeline für Reproducibility
- **UV**: Ultra-fast Python Package Manager

---

## 📊 4. Geodatenhaltung & -vernetzung

### Datenquellen-Integration

**Berlin Geoportal WFS Services**

- **Bezirksgrenzen**: `alkis_bezirke` (Administrative Grenzen)
- **Ortsteile**: `alkis_ortsteile` (Sub-administrative Gebiete)
- **Gebäudedaten**:
  - `alkis_gebaeude` (Gebäudeumrisse)
  - `alkis_geschosshoehen` (Gebäudehöhen & Stockwerke)
- **Verkehrsinfrastruktur**:
  - `radverkehrsnetz` (Fahrradinfrastruktur & Radwege)
  - `detailnetz` (Straßennetz & Verkehrswege)
- **Demografische Daten**: `ua_einwohnerdichte_2024` (Bevölkerungsdichte)
- **ÖPNV-Infrastruktur**: `oepnv_haltestellen` (Bus-, U-Bahn-, S-Bahn-Stationen)

**OpenStreetMap Integration**

- **Overpass API**: ÖPNV Haltestellen

### Geodaten-Harmonisierung Pipeline

**1. CRS Standardisierung**

```python
# Alle Daten → ETRS89/UTM Zone 33N (EPSG:25833)
gdf = gdf.to_crs("EPSG:25833")  # Berlin Standard
```

**2. Räumliche Filterung**

```python
# Automatisches Bezirks-Clipping
buildings_clipped = buildings.clip(district_boundary)
```

**3. Schema-Normalisierung**

```python
# Einheitliche Attribut-Namen
standardized_schema = {
    "id": "feature_id",
    "name": "feature_name",
    "geometry": "geometry"
}
```

**4. Qualitätsbewertung**

```python
quality_score = calculate_data_quality(
    completeness=0.95,
    accuracy=0.90,
    temporal_currency=0.85
)
```

### Metadaten-Management

**Automatisierte Metadaten-Generierung**

- **ISO 19115 konforme** Struktur
- **KI-generierte Beschreibungen** basierend auf Datenanalyse
- **Qualitätsbewertungen** mit Confidence Scores
- **Nutzungsempfehlungen** für GIS-Software
- **Lizenz-Compliance** automatisch integriert

---

## ⚙️ 5. Entwicklungszyklus & Tools

### Agile Entwicklung mit PRP-Methodik

**Product Requirement Prompts (PRPs)**

- **Strukturierte Feature-Planung**: Klare Requirements & Acceptance Criteria
- **Technische Spezifikation**: Detaillierte Implementation Guidelines
- **Test-Driven Development**: Vordefinierte Testing Strategies

**Git Workflow mit Feature Branches**

- **Feature Branch Strategy**: Isolierte Feature-Entwicklung mit Pull Requests
- **Conventional Commits**: Strukturierte commit messages für bessere Traceability
- **Code Review Process**: Automated testing + quality assurance vor Integration (CI Pipeline)

**Claude Code Integration**

- **Automatisierte Dokumentation**: README & API-Docs Generation, Changelog-Management
- **Vorgefertigte Commands**: Spezialisierte Workflows für verschiedene Entwicklungsaufgaben
- **Agent-basierte Entwicklung**: Spezialisierte KI-Agents für Testing, Code Review, Refactoring
- **Agile PRP-Ausführung**: Iterative Entwicklung mit selbstständiger Qualitätsprüfung bis zur vollständigen Funktionalität

**Entwicklungstools**

- **UV Package Manager**: 10x schneller als pip/poetry
- **Docker**: Containerisierte Deployment-Pipeline für Reproducibility
- **Ruff**: Ultra-fast Linting & Formatting
- **MyPy**: Static Type Checking
- **Pytest**: Comprehensive Test Suite

**Quality Assurance Pipeline**

```bash
uv run pytest tests/ -v        # Unit & Integration Tests
uv run ruff check src/         # Code Quality Linting
uv run mypy src/              # Type Checking
uv run pytest --cov=app      # Coverage Analysis
```

---

## 📈 Technische Highlights

### Performance Optimierungen

- **Asynchrone Architektur**: Parallele API-Calls
- **Smart Spatial Filtering**: BBOX Pre-filtering vor geometrischem Clipping
- **Caching Strategy**: Bezirksgrenzen Cache für wiederkehrende Anfragen

### Skalierbarkeit

- **Microservice Ready**: Jeder Service isoliert deploybar
- **Horizontal Scaling**: FastAPI + async für High-Throughput
- **Database Agnostic**: SQLModel ermöglicht PostgreSQL Migration

### Qualitätssicherung

- **Type Safety**: MyPy + Pydantic für 100% Type Coverage
- **Error Resilience**: Comprehensive Exception Handling
- **Monitoring**: Structured Logging für Production Debugging

---

## 🚀 Mögliche Erweiterungen

### Kurzfristig

- **Redis Caching**: Performance-Optimierung für wiederkehrende Anfragen
- **Weitere Datenquellen**: Integration weitere Datenquellen und -layer
- **Kartenvisualisierung**: Interaktive Darstellung der Geodaten im Browser

### Mittelfristig

- **Spatial Analytics**: Buffer-Analysen, Density-Berechnungen, Nachbarschaftsanalysen
- **Analysis Reports**: Automatisierte Analyseberichte entsprechend der Nutzeranfragen
- **Datenqualitäts-Framework**: Standardisierte Bewertungskriterien nach ISO 19157

### Langfristig

- **NLP Web-GIS**: Entwicklung eines vollständigen Web-GIS Systems mit natürlichsprachlicher Bedienung
  - **Conversational GIS**: Dialog-basierte Geodatenanalyse ("Zeige mir Gebäude > Filtere nach Baujahr > Berechne Dichte")
  - **Smart Query Expansion**: Automatische Vorschläge für weiterführende Analysen
  - **Multi-Modal Interface**: Sprache + Karte für intuitive GIS-Bedienung
  - **Collaborative Analytics**: Team-basierte Geodatenanalyse mit geteilten Workspaces

---

## 🎓 Relevanz für Geodatenhaltung & -vernetzung

### Kurs-Bezug

- **Multi-Source Integration**: Heterogene Geodatenquellen vernetzt
- **Metadaten-Standards**: einheitliche Dokumentation
- **CRS Management**: Projektion & Transformation Best Practices
- **Datenqualität**: Automatisierte Qualitätsbewertung & -kontrolle
- **Interoperabilität**: Standardisierte Formate für GIS-Software

### Innovation

- **LLM-Integration**: KI-gestützte Geodaten-Metadaten-Pipeline
- **Natural Language GIS**: Vereinfachung von Geodaten-Zugang
- **Automated Workflows**: Von manueller zu automatisierter Geodatenverarbeitung

---

# AI Documentation Index

This directory contains comprehensive technical documentation for the urbanIQ Berlin geodata aggregation system, organized for AI-assisted development.

## 📋 Documentation Overview

### Core Architecture

- **[SERVICE_ARCHITECTURE.md](./SERVICE_ARCHITECTURE.md)** - Core service design (NLP, Data, Processing, Metadata services)
- **[DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)** - Complete database schema and table definitions
- **[API_DESIGN.md](./API_DESIGN.md)** - REST API endpoints and request/response models

### Implementation Guides

- **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** - Complete implementation plan with 14 structured PRPs
- **[BUILD_INSTRUCTIONS.md](./BUILD_INSTRUCTIONS.md)** - Step-by-step build and setup guide
- **[CONNECTOR_SPECIFICATIONS.md](./CONNECTOR_SPECIFICATIONS.md)** - Detailed API specifications and connector implementations
- **[FRONTEND_IMPLEMENTATION.md](./FRONTEND_IMPLEMENTATION.md)** - HTMX and Tailwind CSS frontend guide
- **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** - Comprehensive testing approach and examples

### Operations

- **[DEPLOYMENT_CONFIGURATION.md](./DEPLOYMENT_CONFIGURATION.md)** - Docker, CI/CD, and production deployment
- **[ERROR_HANDLING_LOGGING.md](./ERROR_HANDLING_LOGGING.md)** - Error handling patterns and logging configuration

## 🛠️ Quick Reference

### Essential Build Information

1. **Prerequisites**: Python 3.11+, UV package manager, GDAL, Google Gemini API key
2. **Setup**: `uv sync --all-extras` → Configure `.env` → `uv run uvicorn app.main:app --reload`
3. **Testing**: `uv run pytest --cov=app`
4. **Quality**: `uv run ruff format .` → `uv run ruff check .` → `uv run mypy app/`

### Key Technologies

- **Backend**: FastAPI + SQLModel + SQLite
- **Geodata**: GeoPandas + Shapely + Fiona
- **LLM**: LangChain + Google Gemini 1.5 Pro
- **Frontend**: HTMX + Jinja2 + Tailwind CSS
- **Package Management**: UV (instead of pip/Poetry)

### Architecture Summary

```
User Request → NLP Service (Gemini) →
Data Service (WFS/OSM) → Processing Service (Harmonization) →
Metadata Service (LLM Report) → ZIP Package Download
```

## 📁 Related Files

### Main Configuration

- **[../CLAUDE.md](../CLAUDE.md)** - Main development guidance for Claude
- **[../pyproject.toml](../pyproject.toml)** - UV package configuration
- **[../.env.example](../.env.example)** - Environment variables template

### Command System

- **[../.claude/commands/](../.claude/commands/)** - Git workflow automation commands

## 🎯 Development Workflow

### New Feature Development

1. Read **SERVICE_ARCHITECTURE.md** for service integration patterns
2. Follow **TESTING_STRATEGY.md** for TDD approach
3. Use **BUILD_INSTRUCTIONS.md** for environment setup
4. Reference **API_DESIGN.md** for endpoint patterns
5. Apply **ERROR_HANDLING_LOGGING.md** for error management

### Production Deployment

1. Follow **BUILD_INSTRUCTIONS.md** for production build
2. Use **DEPLOYMENT_CONFIGURATION.md** for Docker setup
3. Apply **DATABASE_SCHEMA.md** for production database
4. Monitor using patterns from **ERROR_HANDLING_LOGGING.md**

## 📊 System Capabilities

### Data Sources

- **Berlin Geoportal WFS**: Administrative boundaries, transport infrastructure
- **OpenStreetMap Overpass API**: Street networks, points of interest
- **Extensible connector system** for additional sources

### Processing Features

- **Natural language parsing** with Gemini 1.5 Pro
- **Multi-source geodata acquisition** with parallel processing
- **Spatial harmonization** (CRS standardization, clipping, schema normalization)
- **LLM-generated metadata reports** for data quality and usage guidance

### Output Formats

- **Harmonized GeoDataFrames** in ETRS89/UTM33N (EPSG:25833)
- **ZIP packages** with geodata and comprehensive documentation
- **Professional metadata reports** in Markdown format

## 🔄 Migration Notes

This documentation replaces the original `PROJECT_DESCRIPTION.md` file. All information has been:

- ✅ **Distributed** into specialized documentation files
- ✅ **Enhanced** with implementation details and examples
- ✅ **Organized** for efficient AI-assisted development
- ✅ **Integrated** with the Claude command system

The original PROJECT_DESCRIPTION.md can now be safely deleted as all information has been preserved and enhanced in this structured documentation system.

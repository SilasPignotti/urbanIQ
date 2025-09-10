# 📋 CLAUDE.md

This file provides comprehensive guidance to Claude when working with the urbanIQ codebase - a Python-based geodata aggregation and harmonization system for Berlin urban planning.

## 🏙️ System Overview

**urbanIQ Berlin** is an intelligent geodata aggregation system that enables automated district analysis in Berlin through natural language input and LLM-based metadata aggregation.

### Project Goals

- **Primary Objective**: Develop an intelligent geodata aggregator for automated district analyses in Berlin
- **User Interface**: Natural language input processing for geodata requests
- **Output**: Harmonized geodata packages with LLM-generated metadata reports
- **Target Users**: Urban planners, GIS analysts, city administration

### Technical Architecture

The system consists of four core services:

1. **NLP Service**: Gemini-based natural language processing for user request parsing
2. **Data Service**: Orchestrates geodata acquisition from multiple sources (Berlin Geoportal, OpenStreetMap)
3. **Processing Service**: Harmonizes geodata (CRS standardization, spatial clipping, schema normalization)
4. **Metadata Service**: Generates professional metadata reports using LLM analysis

### Key Features

- **Natural Language Interface**: Users can request geodata using plain German text
- **Multi-Source Integration**: Automated data retrieval from Berlin Geoportal WFS and OpenStreetMap
- **Intelligent Processing**: Automatic spatial filtering, CRS transformation, and data harmonization
- **Smart Metadata Generation**: LLM-powered metadata reports for data quality and usage guidance
- **Package Export**: ZIP packages with harmonized geodata and comprehensive documentation

### Development Timeline

- **Phase**: MVP development (7-day sprint)
- **Development Approach**: Iterative development with Claude Code assistance
- **Git Workflow**: Feature branch strategy with automated CI/CD pipeline

## 💡 Core Development Philosophy

### KISS (Keep It Simple, Stupid)

Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

### YAGNI (You Aren't Gonna Need It)

Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

## ⚙️ Core Technologies

**Backend-Framework**:

- **FastAPI**: Asynchrone API-Entwicklung mit automatischer OpenAPI-Dokumentation
- **SQLModel**: Type-safe ORM basierend auf SQLAlchemy und Pydantic
- **SQLite**: Leichtgewichtige Datenbank für Prototyp-Phase

**Package Management**:

- **uv**: Moderner Python Package Manager (anstelle von Poetry/pip)
- **pyproject.toml**: Standardisierte Projektkonfiguration

**Geodatenverarbeitung**:

- **GeoPandas**: Räumliche Datenstrukturen und -operationen
- **Fiona/Shapely**: Low-level Geodaten-I/O und Geometrie-Operationen
- **pyproj**: Koordinatensystem-Transformationen

**LLM-Integration**:

- **LangChain**: Agent-Framework und Prompt-Management
- **google-generativeai**: Google Gemini API Client

**Web-Frontend**:

- **Jinja2**: Template Engine für HTML-Rendering
- **HTMX**: Reaktive Frontend-Interaktionen ohne komplexes JavaScript
- **Tailwind CSS**: Utility-first CSS Framework

## 🧱 Code Structure & Modularity

### File and Function Limits

- **Never create a file longer than 500 lines of code**. If approaching this limit, refactor by splitting into modules.
- **Functions should be under 50 lines** with a single, clear responsibility.
- **Classes should be under 100 lines** and represent a single concept or entity.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
- **Line lenght should be max 100 characters** ruff rule in pyproject.toml

### Design Principles

- **Dependency Inversion**: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- **Open/Closed Principle**: Software entities should be open for extension but closed for modification.
- **Single Responsibility**: Each function, class, and module should have one clear purpose.
- **Fail Fast**: Check for potential errors early and raise exceptions immediately when issues occur.

### Project Architecture

Follow strict vertical slice architecture:

```
geodaten-assistent/
├── pyproject.toml              # uv-Konfiguration und Dependencies
├── .env.example               # Environment-Variablen Template
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml            # CI-Pipeline
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI Application Entry Point
│   ├── config.py            # Settings und Environment-Management
│   ├── database.py          # SQLite Setup und Session Management
│   ├── models/              # SQLModel Definitionen
│   │   ├── __init__.py
│   │   ├── job.py          # Job-Management Models
│   │   ├── package.py      # Download-Package Models
│   │   └── data_source.py  # Datensatz-Registry Models
│   ├── api/                # FastAPI Router
│   │   ├── __init__.py
│   │   ├── deps.py         # Dependency Injection
│   │   ├── chat.py         # Chat-Interface Endpoints
│   │   ├── jobs.py         # Job-Status Endpoints
│   │   └── downloads.py    # Download-Management
│   ├── services/           # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── nlp_service.py      # Gemini-basierte Textanalyse
│   │   ├── data_service.py     # Geodaten-Akquisition
│   │   ├── processing_service.py  # Datenharmonisierung
│   │   ├── metadata_service.py    # LLM-basierte Metadaten-Aggregation
│   │   └── export_service.py     # ZIP-Package-Erstellung
│   ├── connectors/         # Externe API-Abstraktion
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract Base Connector
│   │   ├── geoportal.py    # Berlin WFS/WMS Client
│   │   └── osm.py          # OpenStreetMap Overpass API
│   ├── utils/              # Hilfsfunktionen
│   │   ├── __init__.py
│   │   ├── geo_utils.py    # Geodaten-Utilities
│   │   └── file_utils.py   # Temporäre Dateiverwaltung
│   └── frontend/           # Web-Interface
│       ├── templates/      # Jinja2 Templates
│       │   ├── base.html
│       │   ├── index.html  # Chat-Interface
│       │   └── result.html # Download-Page
│       └── static/         # Assets
│           ├── css/
│           │   └── style.css
│           └── js/
│               └── htmx-extensions.js
├── tests/                  # Test Suite
│   ├── __init__.py
│   ├── conftest.py        # pytest Fixtures
│   ├── test_services/
│   ├── test_connectors/
│   └── test_api/
├── scripts/               # Deployment und Setup
│   ├── setup.py          # Initiales Projekt-Setup
│   └── seed_data.py      # Datensatz-Registry Initialisierung
└── data/                 # Runtime-Dateien
    ├── temp/             # Temporäre Geodaten
    ├── cache/            # API Response Cache
    └── exports/          # Generierte ZIP-Packages
```

## 🛠️ Development Environment

### UV Package Management

This project uses UV for blazing-fast Python package and environment management.

```bash
# Create virtual environment
uv venv

# Sync dependencies
uv sync

# Add a package ***NEVER UPDATE A DEPENDENCY DIRECTLY IN PYPROJECT.toml***
# ALWAYS USE UV ADD
uv add requests

# Add development dependency
uv add --dev pytest ruff mypy

# Remove a package
uv remove requests

# Run commands in the environment
uv run python script.py
uv run pytest
uv run ruff check .

# Install specific Python version
uv python install 3.12
```

### Development Commands

```bash
# Run all tests
uv run pytest

# Run specific tests with verbose output
uv run pytest tests/test_module.py -v

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Type checking
uv run mypy src/

# Run pre-commit hooks
uv run pre-commit run --all-files
```

## 📋 Style & Conventions

### Python Style Guide

- **Follow PEP8** with these specific choices:
  - Line length: 100 characters (set by Ruff in pyproject.toml)
  - Use double quotes for strings
  - Use trailing commas in multi-line structures
- **Always use type hints** for function signatures and class attributes
- **Format with `ruff format`** (faster alternative to Black)
- **Use `pydantic` v2** for data validation and settings management

### Naming Conventions

- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private attributes/methods**: `_leading_underscore`
- **Type aliases**: `PascalCase`
- **Enum values**: `UPPER_SNAKE_CASE`

## 📝 Documentation Standards

### Code Documentation

- Every module should have a docstring explaining its purpose
- Public functions must have complete docstrings
- Complex logic should have inline comments with `# Reason:` prefix
- Keep README.md updated with setup instructions and examples
- Maintain CHANGELOG.md for version history

### Docstring Standards

Use Google-style docstrings for all public functions, classes, and modules:

```python
def calculate_discount(
    price: Decimal,
    discount_percent: float,
    min_amount: Decimal = Decimal("0.01")
) -> Decimal:
    """
    Calculate the discounted price for a product.

    Args:
        price: Original price of the product
        discount_percent: Discount percentage (0-100)
        min_amount: Minimum allowed final price

    Returns:
        Final price after applying discount

    Raises:
        ValueError: If discount_percent is not between 0 and 100
        ValueError: If final price would be below min_amount

    Example:
        >>> calculate_discount(Decimal("100"), 20)
        Decimal('80.00')
    """
```

## 🚨 Error Handling & Logging

### Error Handling

#### Exception Hierarchy

- **Use custom exceptions** for domain-specific errors
- **Inherit from appropriate base classes** (ValueError, ConnectionError, etc.)
- **Provide meaningful error messages** with actionable context

```python
class GeodataError(Exception):
    """Base exception for geodata processing errors"""
    pass

class ConnectorError(GeodataError):
    """Raised when external service connection fails"""
    pass

class DataValidationError(GeodataError):
    """Raised when geodata validation fails"""
    pass
```

#### Error Handling Patterns

- **Fail fast** - validate inputs early and raise exceptions immediately
- **Use try/except sparingly** - only catch exceptions you can handle
- **Log before re-raising** - capture context before propagating errors
- **Provide fallback mechanisms** for non-critical failures

```python
async def fetch_geodata(source_url: str) -> GeodataResponse:
    try:
        response = await http_client.get(source_url, timeout=30)
        response.raise_for_status()
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching geodata from {source_url}")
        raise ConnectorError(f"Service timeout: {source_url}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} from {source_url}")
        raise ConnectorError(f"Service error: {e.response.status_code}")
```

### Logging

#### Logging Configuration

- **Structured logging** with consistent format across services
- **File and console handlers** for development and production
- **Log level control** via environment variables
- **Performance monitoring** for request/response cycles

```python
# Standard logging setup (from config.py)
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("geodaten_assistent")
```

#### Logging Levels & Usage

- **DEBUG**: Detailed diagnostic information, SQL queries, API payloads
- **INFO**: General application flow, job status changes, user actions
- **WARNING**: Recoverable errors, deprecated usage, performance issues
- **ERROR**: Exceptions, failed operations, integration failures
- **CRITICAL**: System failures, data corruption, security breaches

#### Logging Best Practices

```python
# Good: Structured logging with context
logger.info(
    "Job processing started",
    extra={"job_id": job.id, "bezirk": job.bezirk, "categories": job.categories}
)

# Good: Performance logging
start_time = time.time()
# ... processing ...
logger.info(
    f"Geodata processing completed in {time.time() - start_time:.3f}s",
    extra={"job_id": job.id, "records_processed": len(results)}
)

# Bad: Generic messages without context
logger.info("Processing started")
logger.error("Something went wrong")
```

#### Service-Specific Loggers

- **Main app**: `geodaten_assistent`
- **Performance**: `geodaten_assistent.performance`
- **External APIs**: `geodaten_assistent.connectors`
- **Database**: `geodaten_assistent.db`
- **Jobs**: `geodaten_assistent.jobs`

#### Log Management

- **Log rotation** - prevent disk space issues
- **Log retention** - keep logs for debugging and audit trails
- **Sensitive data** - never log API keys, user tokens, or personal data
- **Environment separation** - different log levels for dev/prod

## 🛡️ Security Best Practices

### Security Guidelines

- Never commit secrets - use environment variables
- Validate all user input with Pydantic
- Use parameterized queries for database operations
- Implement rate limiting for APIs
- Keep dependencies updated with `uv`
- Use HTTPS for all external communications
- Implement proper authentication and authorization

## 🧪 Testing Strategy

### Test-Driven Development (TDD)

1. **Write the test first** - Define expected behavior before implementation
2. **Watch it fail** - Ensure the test actually tests something
3. **Write minimal code** - Just enough to make the test pass
4. **Refactor** - Improve code while keeping tests green
5. **Repeat** - One test at a time

### Test Organization

- Unit tests: Test individual functions/methods in isolation
- Integration tests: Test component interactions
- End-to-end tests: Test complete user workflows
- Use `conftest.py` for shared fixtures
- Aim for 80%+ code coverage, but focus on critical paths

## 📚 Useful Resources

### Essential Tools

- UV Documentation: https://github.com/astral-sh/uv
- Ruff: https://github.com/astral-sh/ruff
- Pytest: https://docs.pytest.org/
- Pydantic: https://docs.pydantic.dev/
- FastAPI: https://fastapi.tiangolo.com/

### Python Best Practices

- PEP 8: https://pep8.org/
- PEP 484 (Type Hints): https://www.python.org/dev/peps/pep-0484/
- The Hitchhiker's Guide to Python: https://docs.python-guide.org/

## ⚠️ Important Notes

- **NEVER ASSUME OR GUESS** - When in doubt, ask for clarification
- **Always verify file paths and module names** before use
- **Keep CLAUDE.md updated** when adding new patterns or dependencies
- **Test your code** - No feature is complete without tests

---

_This document serves as the entry point to comprehensive project documentation. Consult the referenced files for detailed guidance on specific topics._

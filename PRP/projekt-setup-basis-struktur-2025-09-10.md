# PRP: Projekt-Setup und Basis-Struktur

## 📖 Context Reading

**Important**: Please read CLAUDE.md completely first and relevant docs from ai-doc/

**Required Documentation:**
- `CLAUDE.md` - Development guidelines and project philosophy (ALWAYS read)
- `ai-doc/SERVICE_ARCHITECTURE.md` - Core service architecture and dependencies
- `ai-doc/API_DESIGN.md` - FastAPI specifications and endpoint design
- `ai-doc/IMPLEMENTATION_ROADMAP.md` - Implementation dependencies and integration points
- `pyproject.toml` - Dependencies and development configuration

## 🎯 Goal

**What should be built**: Complete FastAPI application foundation with main.py, configuration management, structured logging, health check endpoint, dependency injection container, environment variable management, and CORS configuration. Create the foundational architecture that all subsequent services will build upon.

**Success definition**: A fully functional FastAPI application that starts without errors, provides a health check endpoint, loads configuration from environment variables, outputs structured JSON logs, and establishes dependency injection patterns for future service integration.

## 🧑‍💻 User & Use Case

**Target audience**: Development team implementing urbanIQ geodata aggregation system
**Main application**: Foundation for all subsequent development steps (database models, NLP service, connectors, etc.)
**Problem solved**: Establishes consistent project structure, configuration patterns, and development foundation that follows CLAUDE.md guidelines

## ✅ Success Criteria

- [ ] FastAPI application starts successfully with `uv run uvicorn app.main:app --reload`
- [ ] Health check endpoint `/health` returns 200 status with system information
- [ ] Environment variables load correctly from .env file
- [ ] Structured logging outputs JSON format with correlation IDs
- [ ] CORS configuration works for frontend integration
- [ ] Dependency injection container is functional and testable
- [ ] All code follows ruff formatting and passes type checking
- [ ] Basic unit tests pass for configuration and health endpoint

## 🧩 Context & References

### Important Files (if available)

- `CLAUDE.md` - Development guidelines (ALWAYS read)
- `ai-doc/SERVICE_ARCHITECTURE.md` - Service architecture and dependency injection patterns
- `ai-doc/API_DESIGN.md` - API endpoint specifications and error handling
- `ai-doc/IMPLEMENTATION_ROADMAP.md` - Step dependencies and integration requirements
- `pyproject.toml` - Configured dependencies and development tools

### Similar Features in Code

**Current State**: Greenfield implementation - no existing FastAPI patterns to reference
- Existing directory structure: `app/api/`, `app/services/`, `app/models/` (empty __init__.py files)
- Test structure established in `tests/` directory
- Dependencies configured in `pyproject.toml`: FastAPI, Pydantic, SQLModel, structlog

### External References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Structlog: https://www.structlog.org/en/stable/
- SQLModel: https://sqlmodel.tiangolo.com/

## 🏗️ Technical Details

### Main Components

**1. FastAPI Application Setup (app/main.py)**
- Application factory pattern with lifespan management
- Router registration for modular API structure
- CORS middleware configuration
- Global exception handlers
- Request correlation ID middleware

**2. Configuration Management (app/config.py)**
- Pydantic Settings with environment variable support
- Development/production environment detection
- Database connection settings (SQLite for development)
- Logging level configuration
- External service settings (prepared for Gemini API)

**3. Database Foundation (app/database.py)**
- SQLite session management with SQLModel
- Connection pooling configuration
- Session dependency for dependency injection
- Database initialization utilities

**4. Structured Logging Setup**
- JSON output format for production compatibility
- Correlation ID support for request tracking
- Service-specific logger configuration
- Performance logging capabilities

**5. Health Check Endpoint (app/api/health.py)**
- System status monitoring
- Database connection health check
- Service dependency status
- Version information

**6. Dependency Injection (app/api/deps.py)**
- Database session dependency
- Configuration dependency
- Service container pattern for future service integration

### Files to Edit/Create

**New Files:**
- `app/main.py` - FastAPI application entry point (~80 lines)
- `app/config.py` - Pydantic Settings configuration (~60 lines)
- `app/database.py` - Database session management (~40 lines)
- `app/api/health.py` - Health check endpoint (~30 lines)
- `app/api/deps.py` - Dependency injection setup (~25 lines)

**Files to Modify:**
- `app/__init__.py` - Add newline for ruff compliance (1 character fix)

### Dependencies

**Core Dependencies** (already configured in pyproject.toml):
- `fastapi>=0.104.0` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Environment configuration
- `sqlmodel>=0.0.14` - Database ORM
- `python-dotenv>=1.0.0` - Environment file loading
- `structlog>=23.2.0` - Structured logging

**Development Dependencies**:
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `httpx>=0.25.0` - HTTP client for testing

## 🧪 Validation

### Tests

```bash
# Code quality checks
uv run ruff format .
uv run ruff check .
uv run mypy app/

# Run unit tests
uv run pytest tests/ -v

# Test FastAPI startup
uv run uvicorn app.main:app --reload --port 8000

# Manual health check test
curl http://localhost:8000/health
```

### Manual Tests

**1. Application Startup Test:**
```bash
uv run uvicorn app.main:app --reload
# Should start without errors and show "Uvicorn running on..."
```

**2. Health Check Test:**
```bash
curl -X GET http://localhost:8000/health
# Expected: {"status": "ok", "timestamp": "...", "version": "0.1.0"}
```

**3. CORS Test:**
```bash
curl -X OPTIONS http://localhost:8000/health \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
# Should return CORS headers
```

**4. Environment Configuration Test:**
```bash
# Test with different LOG_LEVEL values
LOG_LEVEL=DEBUG uv run uvicorn app.main:app
# Should show debug-level logs
```

### Integration Tests

- FastAPI test client integration
- Database session dependency testing
- Configuration loading validation
- Logging output format verification
- Health endpoint database connectivity check

## 🚫 Anti-Patterns to Avoid

- ❌ Don't hardcode configuration values - use Pydantic Settings
- ❌ Don't ignore the 100-character line limit from ruff configuration
- ❌ Don't create functions longer than 50 lines per CLAUDE.md guidelines
- ❌ Don't skip type hints - all functions must be fully typed
- ❌ Don't use print() statements - use structured logging
- ❌ Don't create global state - use dependency injection
- ❌ Don't ignore error handling - implement proper exception management

## 📝 Implementation Notes

**Environment Variables (.env file should contain):**
```bash
# Application
APP_NAME=urbaniq
APP_VERSION=0.1.0
ENVIRONMENT=development

# Logging
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./data/urbaniq.db

# Future integrations (placeholder)
GOOGLE_API_KEY=your-gemini-api-key-here
```

**Key Implementation Patterns:**
- Follow vertical slice architecture from CLAUDE.md
- Use dependency injection for all external dependencies
- Implement correlation IDs for request tracking
- Prepare service registration patterns for future services
- Follow KISS and YAGNI principles - implement only what's needed now

**Directory Structure After Implementation:**
```
app/
├── __init__.py          # Fixed with newline
├── main.py             # FastAPI app factory
├── config.py           # Pydantic Settings
├── database.py         # SQLite session management
├── api/
│   ├── __init__.py
│   ├── deps.py         # Dependency injection
│   └── health.py       # Health check endpoint
├── models/             # Ready for Schritt 2
├── services/           # Ready for Schritt 3
├── connectors/         # Ready for Schritt 4-5
└── utils/              # Utilities as needed
```

**Testing Strategy:**
- Unit tests for configuration loading and validation
- Integration tests for FastAPI application startup
- Health endpoint functionality testing
- Database session dependency testing

**Future Integration Points:**
- Database models will use the session dependency from database.py
- Services will be registered through dependency injection in deps.py
- API routers will be added to main.py router registration
- Configuration will be extended for external service credentials

---

**Template Version**: Simple v1.0 for University Projects
**Created**: 2025-09-10
**Dependencies**: None (Foundation step)
**Next Step**: Schritt 2 - Database Models und Schema
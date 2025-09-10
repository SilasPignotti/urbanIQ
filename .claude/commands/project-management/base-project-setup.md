---
description: "Initialize project infrastructure: venv, git, docker, CI/CD pipeline"
---

# 🏗️ Base Project Setup

**Context Files**: Please read CLAUDE.md, ai-doc/BUILD_INSTRUCTIONS.md, and ai-doc/DEPLOYMENT_CONFIGURATION.md first.

Initialize complete project infrastructure based on documentation analysis.

## 📖 Documentation Analysis - CRITICAL

**STEP 1 - ALWAYS FIRST**: Read CLAUDE.md completely for project understanding
**STEP 2**: Read all relevant docs from ai-doc/ directory
**STEP 3**: Understand project architecture and requirements

### 1. Core Documentation Review

- **CLAUDE.md** - Project goals, architecture, tech stack, development philosophy
- **CHANGELOG.md** - Current project state and recent changes
- **README.md** (if exists) - Project overview

### 2. Technical Documentation Analysis

- **ai-doc/README.md** - Documentation overview
- **ai-doc/BUILD_INSTRUCTIONS.md** - Build and setup requirements
- **ai-doc/SERVICE_ARCHITECTURE.md** - System architecture
- **ai-doc/DEPLOYMENT_CONFIGURATION.md** - Docker and CI/CD requirements
- **ai-doc/TESTING_STRATEGY.md** - Testing approach

### 3. Infrastructure Requirements Analysis

- Identify Python version and dependency management (UV)
- Understand Docker requirements
- Determine CI/CD pipeline needs
- Identify environment variables and configuration

## 🚀 Infrastructure Setup Process

### Phase 1: Project Configuration Setup

```bash
# Create pyproject.toml based on CLAUDE.md tech stack
# Include: Python 3.11+, UV dependency management, FastAPI, SQLModel, etc.
# Set up project metadata, dependencies, and tool configurations

# Create UV virtual environment
uv venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install initial dependencies (after pyproject.toml is created)
uv sync --all-extras

# Verify Python environment
uv run python --version
uv run which python
```

### Phase 2: Environment Configuration

```bash
# Create .env.example template for team
# Include all necessary environment variables from ai-doc/BUILD_INSTRUCTIONS.md
# Examples: API keys, database URLs, debug settings

# Create .env file for local development
cp .env.example .env  # Then customize with actual values

# Verify environment variables are properly set
```

### Phase 3: Git Repository Setup

```bash
# Initialize git repository (if not already done)
git init

# Create/update .gitignore for Python project
# Include: .venv/, __pycache__/, .env, .pytest_cache/, etc.

# Create basic Git configuration files
# .gitattributes for line endings and file types

# Initial commit structure ready
```

### Phase 4: Docker Configuration

```bash
# Create Dockerfile based on DEPLOYMENT_CONFIGURATION.md
# Multi-stage build for production optimization
# Use Python 3.11+ as specified in CLAUDE.md

# Create docker-compose.yml for local development
# Include services: app, database (if needed)

# Create .dockerignore
# Exclude: .git, .venv, __pycache__, .pytest_cache
```

### Phase 5: CI/CD Pipeline Setup

```bash
# Create GitHub Actions workflow (.github/workflows/)
# Include: test, lint, type-check, build, deploy stages
# Use UV for dependency management
# Follow quality standards from CLAUDE.md

# Create workflow for:
# - Pull request validation
# - Main branch deployment
# - Code quality checks (ruff, mypy, pytest)
```

### Phase 6: Initial Commit and Push

```bash
# Stage all infrastructure files
git add .

# Create initial commit with infrastructure
git commit -m "feat: initial project infrastructure setup

- Add Python project configuration (pyproject.toml)
- Add UV virtual environment configuration
- Add environment variables template (.env.example)
- Add Docker configuration (Dockerfile, docker-compose.yml)
- Add CI/CD pipeline (GitHub Actions)
- Add Git configuration (.gitignore, .gitattributes)
- Set up complete development environment structure"

# Push to main branch (direct push allowed initially)
git branch -M main
git remote add origin <repository-url>  # If not already set
git push -u origin main
```

## ✅ Infrastructure Validation

### Environment Validation

- [ ] pyproject.toml created with proper configuration
- [ ] UV virtual environment created and activated
- [ ] Python version matches CLAUDE.md requirements (3.11+)
- [ ] Dependencies installable via `uv sync`
- [ ] Environment variables template (.env.example) created

### Git Repository Validation

- [ ] Git repository initialized
- [ ] .gitignore includes all necessary exclusions
- [ ] .gitattributes configured for line endings
- [ ] Repository ready for team collaboration

### Docker Validation

- [ ] Dockerfile builds successfully
- [ ] docker-compose.yml runs without errors
- [ ] .dockerignore excludes correct files
- [ ] Multi-stage build optimized for production

### CI/CD Pipeline Validation

- [ ] GitHub Actions workflow syntax valid
- [ ] All quality checks included (ruff, mypy, pytest)
- [ ] UV dependency management integrated
- [ ] Deployment pipeline configured

### Git Integration Validation

- [ ] Initial commit created with all infrastructure
- [ ] Repository pushed to main branch successfully
- [ ] Branch protection can be enabled post-setup
- [ ] Ready for feature branch workflow

## 🚨 Post-Setup Actions

### Manual GitHub Configuration (After Push)

1. **Enable branch protection** for main branch
2. **Require pull request reviews** before merging
3. **Require status checks** to pass before merging
4. **Enable GitHub Actions** if not automatically enabled
5. **Configure repository settings** (description, topics, etc.)

## 📋 Setup Completion Report

**Infrastructure Status:**

1. **Environment**: [UV venv status, Python version, dependencies]
2. **Git Repository**: [Repository URL, initial commit status]
3. **Docker**: [Build status, compose configuration]
4. **CI/CD**: [GitHub Actions status, workflow configuration]
5. **Next Steps**: [Manual GitHub settings, team onboarding]

**Remember**: This setup creates the foundation - actual feature development starts with `/start-feature` → `/prp-create` → `/prp-execute` workflow!

---
description: "Comprehensive project status overview including git, dependencies, and development state"
---

# 📊 Quick Project Status

**Context Files**: Please read .git/config, pyproject.toml, CLAUDE.md, and README.md first.

Comprehensive overview of current project state, git status, and development environment.

---

## 🔄 Git Repository Status

### **Current Branch Information**

```bash
# Active branch and position
git branch --show-current
git status --short
git log --oneline -3

# Relationship to main branch
git fetch origin main >/dev/null 2>&1
git rev-list --count HEAD ^origin/main  # Commits ahead
git rev-list --count origin/main ^HEAD  # Commits behind
```

### **Working Directory State**

```bash
# Changes summary
git status --porcelain | wc -l  # Total modified files
git diff --stat  # Unstaged changes summary
git diff --cached --stat  # Staged changes summary

# Recent activity
git log --oneline --since="1 week ago" | wc -l  # Commits this week
git log --pretty=format:"%h %s" --since="3 days ago"  # Recent commits
```

### **Branch Overview**

```bash
# Local branches
git branch -v | head -10

# Remote tracking status
git remote -v
git ls-remote --heads origin | wc -l  # Remote branches count
```

## 📦 Python Development Environment

### **UV Package Management**

```bash
# UV and Python versions
uv --version 2>/dev/null || echo "⚠️  UV not available"
python --version 2>/dev/null || echo "⚠️  Python not available"

# Project environment status
if [ -f "pyproject.toml" ]; then
    echo "✅ UV project detected (pyproject.toml found)"

    # Check if project is synced
    echo "📦 Project synchronization:"
    uv sync --dry-run 2>/dev/null && echo "  ✅ Dependencies in sync" || echo "  ⚠️  Run 'uv sync' to install/update dependencies"

    # Show main dependencies from pyproject.toml
    echo "📋 Main dependencies (from pyproject.toml):"
    if command -v python >/dev/null 2>&1; then
        python -c "
import sys
try:
    if sys.version_info >= (3, 11):
        import tomllib
        with open('pyproject.toml', 'rb') as f:
            data = tomllib.load(f)
    else:
        import toml
        data = toml.load('pyproject.toml')

    deps = data.get('project', {}).get('dependencies', [])
    for i, dep in enumerate(deps[:8]):
        print(f'  {dep}')
    if len(deps) > 8:
        print(f'  ... and {len(deps)-8} more')
except Exception:
    print('  (Unable to read dependencies)')
" 2>/dev/null
    else
        echo "  (Python not available to parse pyproject.toml)"
    fi

    # Check for dev dependencies
    echo "🛠️  Dev dependencies:"
    python -c "
import sys
try:
    if sys.version_info >= (3, 11):
        import tomllib
        with open('pyproject.toml', 'rb') as f:
            data = tomllib.load(f)
    else:
        import toml
        data = toml.load('pyproject.toml')

    dev_deps = data.get('project', {}).get('optional-dependencies', {}).get('dev', [])
    if dev_deps:
        for dep in dev_deps[:5]:
            print(f'  {dep}')
        if len(dev_deps) > 5:
            print(f'  ... and {len(dev_deps)-5} more')
    else:
        print('  No dev dependencies defined')
except Exception:
    print('  (Unable to read dev dependencies)')
" 2>/dev/null
else
    echo "⚠️  No pyproject.toml found - not a UV project"
fi
```

### **Development Dependencies**

```bash
# Core development tools status
echo "🛠️  Development Tools:"

# Ruff (linting & formatting)
if command -v ruff >/dev/null 2>&1; then
    echo "  ✅ Ruff $(ruff --version | cut -d' ' -f2) - linting & formatting"
else
    echo "  ❌ Ruff not available"
fi

# pytest (testing)
if uv run pytest --version >/dev/null 2>&1; then
    echo "  ✅ pytest $(uv run pytest --version 2>/dev/null | cut -d' ' -f2) - testing framework"
else
    echo "  ❌ pytest not available"
fi

# mypy (type checking)
if uv run mypy --version >/dev/null 2>&1; then
    echo "  ✅ mypy $(uv run mypy --version 2>/dev/null | cut -d' ' -f2) - type checking"
else
    echo "  ❌ mypy not available"
fi
```

## 🧪 Code Quality & Testing

### **Code Quality Status**

```bash
# Run quick code quality checks
echo "🔍 Code Quality Analysis:"

# Ruff linting check
if command -v ruff >/dev/null 2>&1; then
    echo "  📋 Ruff linting:"
    uv run ruff check . --quiet && echo "    ✅ No linting issues" || echo "    ⚠️  Linting issues found"
else
    echo "  ❌ Ruff not available for linting check"
fi

# Type checking with mypy
echo "  🔍 Type checking:"
if uv run mypy --version >/dev/null 2>&1; then
    uv run mypy src/ --quiet && echo "    ✅ No type errors" || echo "    ⚠️  Type errors found"
else
    echo "    ❌ mypy not available"
fi
```

### **Testing Status**

```bash
# Test discovery and status
echo "🧪 Testing Overview:"

if [ -d "tests/" ]; then
    echo "  📁 Test directory: tests/ ($(find tests/ -name "*.py" | wc -l) test files)"
elif [ -d "test/" ]; then
    echo "  📁 Test directory: test/ ($(find test/ -name "*.py" | wc -l) test files)"
else
    echo "  ⚠️  No test directory found"
fi

# Quick test run (without full execution)
if uv run pytest --version >/dev/null 2>&1; then
    echo "  🏃‍♂️ Test runner: pytest available"
    echo "  📊 Test collection:"
    uv run pytest --collect-only -q 2>/dev/null | tail -1 || echo "    No tests collected"
else
    echo "  ❌ pytest not available"
fi
```

### **Build & CI Status**

```bash
# CI/CD configuration
if [ -d ".github/workflows/" ]; then
    echo "🚀 GitHub Actions: $(ls .github/workflows/*.yml 2>/dev/null | wc -l) workflow files"
fi

# Docker setup
[ -f "Dockerfile" ] && echo "🐳 Docker configuration present"
[ -f "docker-compose.yml" ] && echo "🐳 Docker Compose configuration present"
```

## 📈 Project Health Metrics

### **Code Statistics**

```bash
# Project size metrics for Python project
echo "📊 Project Statistics:"
echo "  Total files: $(find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './__pycache__/*' | wc -l)"
echo "  Python files: $(find . -name "*.py" -not -path './.git/*' -not -path './.venv/*' -not -path './__pycache__/*' | wc -l)"
echo "  Test files: $(find . -name "test_*.py" -o -name "*_test.py" -not -path './.venv/*' | wc -l)"
echo "  Documentation files: $(find . -name "*.md" -not -path './.git/*' -not -path './.venv/*' | wc -l)"
echo "  Configuration files: $(find . -maxdepth 2 -name "*.toml" -o -name "*.yaml" -o -name "*.yml" -not -path './.git/*' | wc -l)"
```

### **Recent Activity Analysis**

```bash
# Development velocity
echo "📅 Development Activity:"
echo "  Commits today: $(git log --oneline --since="today" | wc -l)"
echo "  Commits this week: $(git log --oneline --since="1 week ago" | wc -l)"
echo "  Commits this month: $(git log --oneline --since="1 month ago" | wc -l)"

# File change frequency
echo "  Most changed files:"
git log --pretty=format: --name-only --since="1 month ago" | sort | uniq -c | sort -rg | head -5 | sed 's/^[ \t]*/  /'
```

## 🎯 Development Recommendations

### **Immediate Actions Needed**

Analyze current state and suggest priorities:

#### **Git Workflow**

- [ ] **Uncommitted Changes**: Check if any work needs to be committed
- [ ] **Branch Sync**: Determine if branch needs to sync with main
- [ ] **Push Status**: Check if local commits need to be pushed

#### **Code Quality**

- [ ] **Ruff Linting**: Run `uv run ruff check .` and fix issues
- [ ] **Type Checking**: Run `uv run mypy src/` and resolve type errors
- [ ] **Tests**: Execute `uv run pytest` to verify current state
- [ ] **Formatting**: Run `uv run ruff format .` for consistent code style
- [ ] **Dependencies**: Update outdated packages with `uv sync`

#### **Documentation**

- [ ] **README**: Verify documentation reflects current state
- [ ] **CHANGELOG**: Check if recent changes are documented
- [ ] **API Docs**: Update if interfaces have changed

### **Optimization Opportunities**

Based on project analysis:

#### **Performance**

- Review large files or repositories
- Check for unnecessary dependencies
- Analyze test execution time

#### **Security**

- Audit dependencies for vulnerabilities
- Check for exposed secrets or credentials
- Verify access permissions

#### **Maintainability**

- Identify complex or large files needing refactoring
- Check code coverage and test quality
- Review technical debt accumulation

## 🚦 Status Summary

### **Overall Project Health**

- **Git Status**: [Clean/Changes Pending/Conflicts Present]
- **Dependencies**: [Up to Date/Updates Available/Security Issues]
- **Tests**: [Passing/Failing/Not Run Recently]
- **Documentation**: [Current/Needs Update/Missing]

### **Development Readiness**

- **Environment**: [✅ Ready / ⚠️ Setup Needed / ❌ Issues Present]
- **Tools**: [✅ All Available / ⚠️ Some Missing / ❌ Setup Required]
- **Workflow**: [✅ Smooth / ⚠️ Minor Issues / ❌ Blocked]

### **Next Recommended Actions**

1. [Priority action based on analysis]
2. [Secondary action for improvement]
3. [Long-term enhancement suggestion]

---

## 💡 Quick Commands Reference

### **Common Status Checks**

```bash
# Quick git overview
git status && git log --oneline -5

# UV environment and dependency check
uv --version && uv sync --dry-run

# Code quality checks
uv run ruff check . && uv run mypy src/

# Test execution
uv run pytest

# Full quality check
uv run ruff format . && uv run ruff check . && uv run mypy src/ && uv run pytest
```

### **Cleanup Commands**

```bash
# Git cleanup
git gc --prune=now
git remote prune origin

# UV/Python cleanup
uv cache clean
uv sync --reinstall

# Remove Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
```

Ready to understand your project's current state! 📊

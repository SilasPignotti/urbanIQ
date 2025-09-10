---
description: "Initialize new branch and workspace for feature/fix/docs work"
---

# 🚀 Start Feature Work

**Context Files**: Please read .git/config, package.json, and pyproject.toml first.

Initialize a new branch and prepare workspace for development work.

## 📝 Work Details

**Description:** $ARGUMENTS

## 🎯 Branch Type Selection

Analyze the work description and determine the appropriate branch type:

- **`feature/*`** - New functionality, enhancements, or capabilities
- **`fix/*`** - Bug fixes, error corrections, or issue resolutions
- **`docs/*`** - Documentation updates, README changes, or guides
- **`refactor/*`** - Code restructuring, optimization, or cleanup
- **`test/*`** - Adding or improving tests
- **`chore/*`** - Maintenance tasks, dependency updates, or tooling

## 🔄 Initialization Process

### **Step 1: Environment Preparation**

```bash
# Ensure clean working directory
git status

# Switch to main and get latest changes
git checkout main
git pull origin main

# Verify no uncommitted changes
git diff --staged
```

### **Step 2: Branch Creation**

Based on work description, create appropriately named branch:

```bash
# Create and checkout new branch
git checkout -b [type]/[descriptive-name]

# Examples:
# git checkout -b feature/user-authentication
# git checkout -b fix/database-connection-timeout
# git checkout -b docs/api-documentation
```

### **Step 3: Workspace Setup**

```bash
# Verify development environment
python --version
uv --version  # Check UV package manager

# Check project dependencies
uv sync --check

# Run initial tests to ensure baseline
uv run pytest

# Check for any immediate issues
git log --oneline -5
```

## 📋 Branch Naming Convention

### **Format:** `[type]/[short-descriptive-name]`

### **Guidelines:**

- ✅ Use lowercase with hyphens
- ✅ Be descriptive but concise (max 50 chars)
- ✅ Include main functionality/fix area
- ❌ No spaces, underscores, or special chars
- ❌ No issue numbers (use in commits instead)

### **Examples:**

```
feature/district-name-fuzzy-search
fix/wfs-timeout-handling
docs/api-endpoints-documentation
refactor/data-harmonizer-structure
test/crs-transformation-edge-cases
chore/update-dependencies
```

## ✅ Pre-Work Checklist

Before starting development, verify:

- [ ] **Clean State**: No uncommitted changes in main
- [ ] **Latest Code**: Main branch is up to date
- [ ] **Branch Created**: New branch follows naming convention
- [ ] **Environment Ready**: Dependencies installed and tests pass
- [ ] **Context Clear**: Work scope and objectives understood

## 📊 Workspace Status Report

After initialization, provide:

### **Branch Information**

- **Branch Name**: [Generated branch name]
- **Base Commit**: [Latest main commit hash and message]
- **Work Type**: [Determined work category]

### **Environment Status**

- **Dependencies**: [Status of package installations]
- **Tests**: [Baseline test results]
- **Tools**: [Linting, formatting tools status]

### **Next Steps**

- **Immediate Tasks**: [First development steps]
- **Key Files**: [Likely files to be modified]
- **Testing Strategy**: [How to validate changes with UV]

---

Ready to start productive development! 🎯

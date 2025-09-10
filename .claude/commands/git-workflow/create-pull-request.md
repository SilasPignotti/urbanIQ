---
description: "Run pre-PR tests, create pull request with template, and setup CI pipeline"
---

# 🔄 Create Pull Request

**Context Files**: Please read .github/pull_request_template.md, pyproject.toml, CLAUDE.md, and .github/workflows/ first.

Execute pre-PR validation, create structured pull request, and ensure CI pipeline readiness.

## 📝 PR Context

**Additional Details:** $ARGUMENTS

---

## 🧪 Pre-PR Validation Pipeline

### **Step 1: Code Quality Checks**

#### **Linting & Formatting**

```bash
# Ruff formatting check
echo "🎨 Checking code formatting..."
uv run ruff format --check . || {
    echo "❌ Code formatting issues found. Run: uv run ruff format ."
    exit 1
}

# Ruff linting check
echo "🔍 Running linting checks..."
uv run ruff check . || {
    echo "❌ Linting issues found. Run: uv run ruff check --fix ."
    exit 1
}

# Type checking with mypy
echo "🔍 Running type checks..."
uv run mypy src/ || {
    echo "❌ Type checking failed. Fix type errors before creating PR."
    exit 1
}

# Check for debug statements and breakpoints
echo "🔍 Checking for debug code..."
grep -r "pdb\.set_trace\|breakpoint()\|print(" src/ && {
    echo "❌ Debug statements found. Remove before creating PR."
    exit 1
} || echo "✅ No debug statements found"
```

#### **Security & Dependencies**

```bash
# Check UV project sync status
echo "📦 Checking dependency synchronization..."
uv sync --dry-run || {
    echo "❌ Dependencies out of sync. Run: uv sync"
    exit 1
}

# Security check for sensitive data in changes
echo "🔐 Checking for sensitive data..."
git diff main --name-only | xargs grep -l "password\|secret\|key\|token\|api.*key" 2>/dev/null && {
    echo "❌ Potential sensitive data found in changes. Review carefully."
    exit 1
} || echo "✅ No sensitive data detected"

# Check for hardcoded secrets in new code
git diff main | grep -E "\+.*['\"].*[a-zA-Z0-9]{20,}['\"]" && {
    echo "⚠️  Potential hardcoded secrets detected. Please review."
} || echo "✅ No hardcoded secrets detected"
```

### **Step 2: Test Execution**

#### **Unit Tests**

```bash
# Run pytest with coverage
echo "🧪 Running unit tests..."
if [ -d "tests/" ] || [ -d "test/" ]; then
    uv run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=80 || {
        echo "❌ Tests failed or coverage below 80%. Fix tests before creating PR."
        exit 1
    }
    echo "✅ All tests passed with sufficient coverage"
else
    echo "⚠️  No test directory found. Consider adding tests."
fi
```

#### **Integration Tests**

```bash
# Run integration tests if they exist
echo "🔗 Running integration tests..."
if [ -d "tests/integration/" ]; then
    uv run pytest tests/integration/ -v || {
        echo "❌ Integration tests failed. Fix before creating PR."
        exit 1
    }
    echo "✅ Integration tests passed"
else
    echo "ℹ️  No integration tests found"
fi

# Check if any test configuration files need updates
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
    echo "✅ Test configuration files present"
fi
```

#### **Build Verification**

```bash
# Verify project can be installed in development mode
echo "🔨 Verifying project installation..."
uv sync || {
    echo "❌ Project installation failed. Check pyproject.toml"
    exit 1
}

# Check if project has entry points or scripts
if grep -q "scripts\|entry-points" pyproject.toml 2>/dev/null; then
    echo "✅ Project scripts/entry-points configured"
fi

# Docker build test (if Dockerfile exists)
if [ -f "Dockerfile" ]; then
    echo "🐳 Testing Docker build..."
    docker build -t test-build . || {
        echo "❌ Docker build failed"
        exit 1
    }
    echo "✅ Docker build successful"
fi
```

### **Step 3: Branch Synchronization**

#### **Rebase with Main**

```bash
# Fetch latest changes
git fetch origin main

# Check if rebase is needed
git merge-base --is-ancestor main HEAD || {
    echo "Rebase required - main has new commits"
    git rebase origin/main
}

# Verify clean state after rebase
git status --porcelain
```

## 📋 Pull Request Creation

### **Branch Analysis**

Extract information for PR template:

#### **Change Summary**

- **Branch Type**: [feature/fix/docs/refactor]
- **Scope**: [Affected components/modules]
- **Files Changed**: [Count and primary locations]
- **Complexity**: [Simple/Medium/Complex based on changes]

#### **Commit Analysis**

```bash
# Get commit messages for PR description
git log main..HEAD --oneline
git log main..HEAD --pretty=format:"- %s"

# Analyze change patterns
git diff main --stat
git diff main --shortstat
```

### **PR Template Population**

#### **Standard Template Structure**

````markdown
## 📋 Change Summary

### What Changed

- [Bullet points describing key changes]

### Why Changed

- [Business/technical justification]

### How It Works

- [Brief technical explanation]

## 🧪 Testing

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests verified
- [ ] Manual testing completed

### Test Commands

```bash
# Commands to verify the changes
uv run pytest -v --cov=src
uv run ruff check . && uv run ruff format --check .
uv run mypy src/
```
````

## 🔍 Review Checklist

### Code Quality

- [ ] Code follows project standards
- [ ] No hardcoded values or secrets
- [ ] Error handling is appropriate
- [ ] Performance considerations addressed

### Documentation

- [ ] README updated if needed
- [ ] API documentation current
- [ ] Inline comments for complex logic
- [ ] CHANGELOG entry added

### Security & Performance

- [ ] No security vulnerabilities introduced
- [ ] Performance impact assessed
- [ ] Database migrations tested
- [ ] Breaking changes documented

## 🚀 Deployment Notes

### Environment Impact

- [ ] Development environment tested
- [ ] Staging deployment plan ready
- [ ] Production considerations documented

### Migration Requirements

- [ ] Database changes documented
- [ ] Configuration updates needed
- [ ] Dependency updates required

---

Closes #[issue-number]

````

### **PR Creation Command**
```bash
# Push current branch
git push origin $(git branch --show-current)

# Create PR using GitHub CLI
gh pr create \
  --title "[Auto-generated title based on commits]" \
  --body-file .github/pr_body.md \
  --base main \
  --head $(git branch --show-current) \
  --assignee @me

# Alternative: Provide GitHub URL for manual creation
echo "Create PR at: https://github.com/[user]/[repo]/compare/main...$(git branch --show-current)"
````

## 🔄 CI/CD Pipeline Setup

### **Workflow Verification**

#### **GitHub Actions Status**

```bash
# Check if workflow files exist
ls -la .github/workflows/

# Validate workflow syntax
gh workflow list
gh workflow view [workflow-name]
```

#### **Pipeline Jobs Expected**

- **Code Quality**: Ruff linting & formatting, mypy type checking
- **Testing**: pytest unit tests with coverage reporting
- **Build**: UV sync and project installation verification
- **Security**: Dependency vulnerability scanning

### **Status Check Requirements**

Configure branch protection rules:

```yaml
required_status_checks:
  strict: true
  contexts:
    - "ci/ruff-lint"
    - "ci/ruff-format"
    - "ci/mypy"
    - "ci/pytest"
    - "ci/uv-sync"
```

## 📊 PR Quality Report

### **Validation Results**

- **Ruff Linting**: [✅ Pass / ❌ Fail with details]
- **Ruff Formatting**: [✅ Pass / ❌ Needs formatting]
- **Type Checking**: [✅ Pass / ❌ Type errors found]
- **Tests**: [Coverage percentage and pass/fail status]
- **UV Sync**: [✅ Dependencies in sync / ❌ Sync required]

### **Change Metrics**

- **Files Modified**: [Count and breakdown by type]
- **Lines Added/Removed**: [Net change statistics]
- **Test Coverage**: [Before/after coverage comparison]
- **Complexity Score**: [Simple/Medium/Complex assessment]

### **Review Readiness**

- **Documentation**: [Complete/needs update]
- **Testing**: [Comprehensive/adequate/needs work]
- **Dependencies**: [None/minor/major updates]
- **Breaking Changes**: [None/documented/requires migration]

## 🎯 Post-PR Actions

### **Immediate Next Steps**

1. **Monitor CI Pipeline**: Watch for any failures
2. **Address Feedback**: Respond to review comments promptly
3. **Update Documentation**: Based on review feedback
4. **Prepare for Merge**: Ensure all checks pass

### **Merge Strategy**

Based on branch type and changes:

- **Feature Branches**: Squash and merge (clean history)
- **Hotfixes**: Merge commit (preserve urgency context)
- **Documentation**: Squash and merge (simplified history)

### **Post-Merge Cleanup**

```bash
# After successful merge
git checkout main
git pull origin main
git branch -d feature/branch-name  # Delete local branch
git push origin --delete feature/branch-name  # Delete remote branch
```

---

## ⚠️ Common Issues & Solutions

### **Pre-PR Failures**

- **Test Failures**: Run `uv run pytest -v` and fix failing tests
- **Ruff Issues**: Run `uv run ruff check --fix .` and `uv run ruff format .`
- **Type Errors**: Run `uv run mypy src/` and fix type issues
- **Merge Conflicts**: Rebase with main using `git rebase origin/main`
- **Dependency Issues**: Run `uv sync` to resolve dependency problems

### **CI Pipeline Issues**

- **Flaky Tests**: Re-run with `uv run pytest --lf` (last failed) or investigate root cause
- **UV Sync Failures**: Check pyproject.toml syntax and dependency compatibility
- **Timeout Issues**: Optimize test execution or increase CI timeout limits
- **mypy Cache Issues**: Clear cache with `uv run mypy --clear-cache`

Ready to create professional pull requests with comprehensive validation! 🚀

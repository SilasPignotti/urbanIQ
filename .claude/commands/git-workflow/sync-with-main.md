---
description: "Safely synchronize current branch with main branch using rebase or merge"
---

# 🔄 Sync with Main Branch

**Context Files**: Please read .git/config, pyproject.toml, and CLAUDE.md first.

Safely synchronize your current feature branch with the latest main branch changes.

## 📝 Sync Context

**Additional Instructions:** $ARGUMENTS

---

## 🔍 Pre-Sync Analysis

### **Current State Assessment**

```bash
# Check current branch and status
git branch --show-current
git status --porcelain

# Analyze divergence from main
git fetch origin main
git log --oneline $(git merge-base HEAD main)..main  # New commits in main
git log --oneline $(git merge-base HEAD main)..HEAD  # Your commits
```

### **Divergence Report**

- **Your Branch**: [Current branch name]
- **Commits Ahead**: [Number of your commits not in main]
- **Commits Behind**: [Number of main commits you don't have]
- **Last Common Commit**: [Merge base information]

## ⚙️ Sync Strategy Selection

### **Strategy Decision Matrix**

#### **🎯 Rebase (Recommended for Solo Development)**

**Use When:**

- Clean, linear history desired
- Your commits are logical and atomic
- No merge commits needed
- Feature branch is private (not shared)

**Benefits:**

- ✅ Linear project history
- ✅ Cleaner commit graph
- ✅ Easier to understand change progression
- ✅ Better for solo development

#### **🔀 Merge (Use for Collaborative Features)**

**Use When:**

- Preserving exact development history
- Branch has been shared with others
- Complex branching structure exists
- Merge commits provide value

**Benefits:**

- ✅ Preserves exact development timeline
- ✅ Safe for shared branches
- ✅ No history rewriting
- ✅ Clear feature integration points

## 🎯 Rebase Execution

### **Interactive Rebase Process**

```bash
# Ensure clean working directory
git status
git stash push -m "WIP: before sync" || true

# Start interactive rebase
git rebase -i origin/main

# During rebase, you can:
# - pick: use commit as-is
# - reword: change commit message
# - edit: modify commit content
# - squash: combine with previous commit
# - drop: remove commit entirely
```

### **Conflict Resolution During Rebase**

When conflicts occur:

```bash
# View conflicted files
git status
git diff --name-only --diff-filter=U

# Resolve conflicts in each file
# Edit conflicted files to resolve <<<<< ===== >>>>> markers

# Stage resolved files
git add <resolved-files>

# Continue rebase
git rebase --continue

# Or abort if needed
git rebase --abort
```

### **Rebase Completion**

```bash
# Verify rebase success
git log --oneline -10
git log --graph --oneline -10

# Force push updated branch (careful!)
git push --force-with-lease origin $(git branch --show-current)
```

## 🔀 Merge Execution

### **Standard Merge Process**

```bash
# Ensure clean working directory
git status
git stash push -m "WIP: before sync" || true

# Switch to main and pull latest
git checkout main
git pull origin main

# Switch back and merge
git checkout -
git merge main

# Or create merge commit
git merge --no-ff main -m "Merge latest main into feature branch"
```

### **Conflict Resolution During Merge**

```bash
# View merge conflicts
git status
git diff --name-only --diff-filter=U

# Resolve conflicts and stage
git add <resolved-files>

# Complete merge
git commit -m "Resolve merge conflicts with main"

# Push updated branch
git push origin $(git branch --show-current)
```

## 🧪 Post-Sync Validation

### **Integrity Checks**

```bash
# Verify UV dependencies are still in sync
echo "📦 Checking dependency sync after merge..."
uv sync --dry-run || {
    echo "⚠️  Dependencies may need resync after merge"
    uv sync
}

# Run quick code quality checks
echo "🔍 Running post-sync validation..."
uv run ruff check . --quiet || echo "⚠️  Linting issues detected after sync"
uv run mypy src/ --quiet || echo "⚠️  Type checking issues detected after sync"

# Verify tests still pass
if [ -d "tests/" ] || [ -d "test/" ]; then
    echo "🧪 Running tests after sync..."
    uv run pytest --maxfail=5 -q || {
        echo "❌ Tests failing after sync. Review conflicts resolution."
        exit 1
    }
    echo "✅ Tests passing after sync"
else
    echo "ℹ️  No tests to run"
fi

# Check for any Python syntax errors in modified files
echo "🐍 Checking Python syntax..."
git diff --name-only HEAD~1 | grep "\.py$" | xargs -I {} python -m py_compile {} 2>/dev/null || echo "⚠️  Python syntax issues detected"

# Validate no files were corrupted
git status --porcelain
```

### **History Verification**

```bash
# Confirm sync was successful
git log --oneline $(git merge-base HEAD main)..HEAD  # Your commits after sync
git log --oneline main..HEAD  # Commits unique to your branch

# Visual confirmation
git log --graph --oneline -15
```

## 📊 Sync Summary Report

### **Sync Results**

- **Strategy Used**: [Rebase/Merge]
- **Conflicts Resolved**: [Count and files]
- **Final State**: [Commits ahead/behind main]
- **Branch Integrity**: [✅ Maintained / ⚠️ Issues detected]

### **Change Analysis**

- **New Commits from Main**: [List of integrated commits]
- **Your Commits Preserved**: [List of your commits after sync]
- **Files Affected by Sync**: [Files that had conflicts or changes]

### **Validation Status**

- **UV Sync Status**: [✅ Dependencies in sync / ❌ Resync required]
- **Tests Status**: [✅ Pass / ❌ Fail]
- **Ruff Linting**: [✅ Pass / ❌ Issues found]
- **Type Checking**: [✅ Pass / ❌ Type errors]
- **Python Syntax**: [✅ Valid / ❌ Syntax errors]

## 🚨 Emergency Procedures

### **If Sync Goes Wrong**

```bash
# Find your branch before sync
git reflog --oneline -10

# Reset to previous state
git reset --hard HEAD@{n}  # where n is the entry before sync

# Or create recovery branch
git branch recovery-branch HEAD@{n}
```

### **Common Issues & Solutions**

#### **Too Many Conflicts**

```bash
# Abort current operation
git rebase --abort  # or git merge --abort

# Try alternative strategy
# If rebasing failed, try merge instead
```

#### **Lost Commits**

```bash
# Use reflog to find lost commits
git reflog --oneline -20
git cherry-pick <lost-commit-hash>
```

#### **Corrupted Branch State**

```bash
# Create clean branch from backup
git checkout -b branch-name-fixed origin/main
git cherry-pick <commit1> <commit2> <commit3>
```

---

## 💡 Best Practices

### **Before Syncing**

- ✅ **Commit all work** - no dirty working directory
- ✅ **Run tests** - ensure `uv run pytest` passes
- ✅ **Check dependencies** - ensure `uv sync --dry-run` is clean
- ✅ **Backup** - note current commit hash

### **During Sync**

- ✅ **Resolve conflicts carefully** - understand both sides
- ✅ **Test after each conflict** - run `uv run pytest --maxfail=5`
- ✅ **Check code quality** - run `uv run ruff check .` after resolutions
- ✅ **Keep commits focused** - don't mix sync and feature work
- ✅ **Document complex resolutions** - help future you

### **After Sync**

- ✅ **Validate thoroughly** - run full quality pipeline
- ✅ **Dependencies sync** - run `uv sync` if needed
- ✅ **Update documentation** - if integration affects docs
- ✅ **Run complete validation**: `uv run ruff format . && uv run ruff check . && uv run mypy src/ && uv run pytest`

Ready to safely synchronize your branch! 🔄

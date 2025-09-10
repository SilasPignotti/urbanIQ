---
description: "Safe cleanup of merged, stale, and unnecessary git branches"
---

**Context Files**: Please read .git/config first.

# 🧹 Cleanup Branches

Safely identify and remove merged, stale, and unnecessary git branches to maintain repository hygiene.

## 📝 Cleanup Context

**Additional Instructions:** $ARGUMENTS

---

## 🔍 Branch Analysis

### **Current Branch Inventory**

```bash
# Local branches overview
git branch -v
echo "Total local branches: $(git branch | wc -l)"

# Remote branches overview
git branch -r
echo "Total remote branches: $(git branch -r | wc -l)"

# Branch activity analysis
git for-each-ref --format='%(refname:short) %(committerdate:short) %(authorname)' --sort=-committerdate refs/heads/
```

### **Merge Status Analysis**

```bash
# Branches merged into main
git branch --merged main | grep -v main | grep -v '^\*'

# Branches not yet merged
git branch --no-merged main | grep -v '^\*'

# Recently active branches (last 30 days)
git for-each-ref --format='%(refname:short) %(committerdate:relative)' --sort=-committerdate refs/heads/ | head -10
```

## 🎯 Cleanup Categories

### **Safe to Delete: Merged Branches**

#### **Fully Merged Branches**

Branches that have been completely merged into main:

```bash
# Identify merged branches (excluding main and current)
MERGED_BRANCHES=$(git branch --merged main | grep -v main | grep -v '^\*' | tr -d ' ')

if [ -n "$MERGED_BRANCHES" ]; then
    echo "📋 Merged branches found:"
    echo "$MERGED_BRANCHES"
else
    echo "✅ No merged branches to clean up"
fi
```

#### **Remote-Deleted Branches**

Local branches tracking deleted remote branches:

```bash
# Find branches with deleted remote tracking
git remote prune origin --dry-run

# Local branches without remote counterpart
git branch -vv | grep ': gone' | awk '{print $1}' || echo "No orphaned branches"
```

### **Review Required: Stale Branches**

#### **Old Inactive Branches**

Branches not updated recently:

```bash
# Branches older than 30 days
echo "📅 Branches older than 30 days:"
git for-each-ref --format='%(refname:short) %(committerdate:short)' refs/heads/ | \
while read branch date; do
    if [ "$branch" != "main" ] && [ $(date -d "$date" +%s) -lt $(date -d "30 days ago" +%s) ]; then
        echo "  $branch (last updated: $date)"
    fi
done
```

#### **Naming Convention Violations**

Branches not following project conventions:

```bash
# Find branches not following feature/fix/docs/refactor pattern
git branch | grep -v main | grep -v '^\*' | grep -v -E '(feature|fix|docs|refactor|test|chore)/' || echo "All branches follow naming convention"
```

## 🗑️ Safe Cleanup Operations

### **Phase 1: Merged Branch Cleanup**

```bash
# Delete local merged branches (excluding main and current)
MERGED_BRANCHES=$(git branch --merged main | grep -v main | grep -v '^\*' | tr -d ' ')

for branch in $MERGED_BRANCHES; do
    echo "🗑️  Deleting merged branch: $branch"
    git branch -d "$branch"
done
```

### **Phase 2: Remote Tracking Cleanup**

```bash
# Remove stale remote tracking references
git remote prune origin

# Delete local branches with deleted remotes
git branch -vv | grep ': gone' | awk '{print $1}' | while read branch; do
    echo "🗑️  Deleting orphaned branch: $branch"
    git branch -D "$branch"
done
```

### **Phase 3: Remote Branch Cleanup**

```bash
# List remote branches that are merged (be careful!)
git branch -r --merged main | grep -v main | grep -v HEAD | sed 's/origin\///'

# Only delete if you're sure they're no longer needed
# git push origin --delete branch-name
```

## ⚠️ Interactive Review Process

### **Stale Branch Review**

For branches requiring manual review:

#### **Branch Information Template**

For each questionable branch, provide:

```markdown
### Branch: [branch-name]

- **Last Updated**: [date]
- **Author**: [author-name]
- **Commits Ahead**: [number of commits not in main]
- **Status**: [merged/unmerged/stale]
- **Files Changed**: [count and main areas]
- **Recommendation**: [keep/delete/archive]
```

#### **Decision Matrix**

- **Keep**: Active development, recent commits, unmerged features
- **Delete**: Merged branches, abandoned experiments, duplicate work
- **Archive**: Important but inactive, create tag before deletion

### **Batch Operations**

```bash
# Create archive tags for important branches before deletion
git tag archive/branch-name branch-name
git branch -D branch-name

# Bulk delete after confirmation
echo "feature/old-experiment fix/obsolete-bug docs/outdated-guide" | tr ' ' '\n' | xargs -I {} git branch -D {}
```

## 🏷️ Branch Archiving Strategy

### **Create Archive Tags**

Before deleting potentially important branches:

```bash
# Tag branches for historical reference
git tag archive/$(date +%Y%m%d)/branch-name branch-name
git push origin archive/$(date +%Y%m%d)/branch-name

# Then safely delete the branch
git branch -D branch-name
git push origin --delete branch-name
```

### **Archive Categories**

- `archive/experiments/` - Experimental features or POCs
- `archive/deprecated/` - Deprecated functionality
- `archive/backup/` - Safety backup before major changes
- `archive/YYYYMMDD/` - Date-based archiving

## 📊 Cleanup Summary Report

### **Cleanup Statistics**

- **Branches Deleted**: [Count of removed local branches]
- **Remote References Pruned**: [Count of stale remote refs removed]
- **Branches Archived**: [Count of branches tagged before deletion]
- **Space Saved**: [Estimated repository size reduction]

### **Repository State After Cleanup**

```bash
# Final branch count
echo "Local branches remaining: $(git branch | wc -l)"
echo "Remote branches: $(git branch -r | wc -l)"

# Most recent activity
echo "Recent active branches:"
git for-each-ref --format='%(refname:short) %(committerdate:relative)' --sort=-committerdate refs/heads/ | head -5
```

### **Recommendations for Future**

- **Regular Cleanup**: Schedule monthly branch maintenance
- **Naming Conventions**: Enforce consistent branch naming
- **Merge Strategy**: Prefer squash merges to reduce branch noise
- **Automated Cleanup**: Consider GitHub/GitLab auto-delete merged branches

## 🚨 Recovery Procedures

### **If Wrong Branch Deleted**

```bash
# Find deleted branch in reflog
git reflog --all | grep "branch-name"

# Restore from reflog entry
git branch branch-name HEAD@{n}  # where n is the reflog entry

# Or restore from archive tag
git checkout -b branch-name archive/YYYYMMDD/branch-name
```

### **Restore Remote Branch**

```bash
# If accidentally deleted remote branch
git push origin local-branch-name:remote-branch-name

# Or push archive tag back to branch
git push origin archive/YYYYMMDD/branch-name:refs/heads/branch-name
```

## 🛡️ Safety Guidelines

### **Before Cleanup**

- ✅ **Backup Important Work**: Ensure no uncommitted changes
- ✅ **Team Communication**: Notify team of shared branch cleanup
- ✅ **Archive Strategy**: Tag important branches before deletion
- ✅ **Double Check Merges**: Verify branches are truly merged

### **During Cleanup**

- ✅ **Incremental Approach**: Delete a few branches at a time
- ✅ **Verify Each Deletion**: Check branch content before removal
- ✅ **Keep Notes**: Document what was cleaned and why
- ✅ **Test After Cleanup**: Ensure repository still functions

### **After Cleanup**

- ✅ **Validate Repository**: Check out main and run tests
- ✅ **Update Documentation**: Note any workflow changes
- ✅ **Monitor for Issues**: Watch for any missing references
- ✅ **Schedule Next Cleanup**: Set reminder for future maintenance

---

## 💡 Best Practices for Branch Hygiene

### **Preventive Measures**

- **Consistent Naming**: Use clear, descriptive branch names
- **Regular Merging**: Don't let feature branches get too stale
- **Auto-Delete**: Enable auto-delete for merged branches in GitHub/GitLab
- **Team Policies**: Establish branch lifecycle guidelines

### **Maintenance Schedule**

- **Weekly**: Check for merged branches to delete
- **Monthly**: Review stale branches and clean up
- **Quarterly**: Comprehensive cleanup and archiving
- **Yearly**: Major repository maintenance and optimization

Ready to maintain a clean, organized repository! 🧹

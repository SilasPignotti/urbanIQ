---
description: "Analyze changes and create smart conventional commits with proper staging"
---

# 💾 Intelligent Commit Generator

**Context Files**: Please read .git/config and CHANGELOG.md first.

Analyze code changes and create well-structured conventional commits with smart staging recommendations.

## 📝 Additional Context

**Extra Instructions:** $ARGUMENTS

---

## 🔍 Change Analysis Process

### **Step 1: Repository State Assessment**

```bash
# Check current working directory status
git status --porcelain

# Review staged changes
git diff --staged --stat
git diff --staged --name-only

# Review unstaged changes
git diff --stat
git diff --name-only
```

### **Step 2: Change Categorization**

Analyze modified files and categorize changes:

#### **🆕 New Features (`feat`)**

- New functionality or capabilities
- New API endpoints or methods
- User-facing feature additions
- New components or modules

#### **🐛 Bug Fixes (`fix`)**

- Error corrections and bug resolutions
- Performance issue fixes
- Security vulnerability patches
- Edge case handling improvements

#### **📚 Documentation (`docs`)**

- README updates
- API documentation changes
- Code comments and docstrings
- User guides and tutorials

#### **🎨 Code Style (`style`)**

- Formatting changes (prettier, black)
- Whitespace, semicolons, indentation
- Code organization without logic changes
- Import statement reorganization

#### **♻️ Refactoring (`refactor`)**

- Code restructuring without behavior change
- Function/class/variable renaming
- Code simplification and cleanup
- Architecture improvements

#### **⚡ Performance (`perf`)**

- Performance optimizations
- Algorithm improvements
- Database query optimization
- Memory usage improvements

#### **🧪 Tests (`test`)**

- Test additions and modifications
- Test coverage improvements
- Test infrastructure changes
- Mock and fixture updates

#### **🔧 Maintenance (`chore`)**

- Dependency updates
- Build process changes
- CI/CD configuration
- Development tool updates

## 📋 Staging Strategy

### **Smart Staging Recommendations**

Based on change analysis, suggest optimal staging strategy:

#### **Atomic Commits Approach**

- **Single Feature/Fix**: Stage all related files together
- **Multiple Changes**: Suggest separate commits for different concerns
- **Mixed Changes**: Recommend staging by logical groupings

#### **File Grouping Logic**

```bash
# Group related changes
git add src/feature-a/  # Feature files together
git add tests/test_feature_a.py  # Related tests
git add docs/feature-a.md  # Related documentation

# Separate unrelated changes
git reset  # Unstage everything
git add specific-files-for-commit-1
# Create first commit
git add specific-files-for-commit-2
# Create second commit
```

## 📝 Commit Message Generation

### **Conventional Commit Format**

Never include claude code, or written by claude code in commit messages!

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### **Message Construction Rules**

#### **Type Selection**

- Analyze primary change category
- Use most specific applicable type
- Default to `chore` for mixed/unclear changes

#### **Scope Determination**

- Extract from file paths and function names
- Use module/component names
- Keep scope concise (1-2 words max)
- Optional for broad changes

#### **Description Guidelines**

- Start with lowercase verb (add, fix, update, remove)
- Be specific and actionable
- Max 50 characters for summary line
- Focus on **what** changed, not **how**

#### **Body Content (when needed)**

- Explain **why** the change was made
- Describe any breaking changes
- Reference related issues/PRs
- Include migration notes if applicable

### **Quality Checklist**

- [ ] Type accurately reflects change category
- [ ] Scope is relevant and concise
- [ ] Description is clear and specific
- [ ] No mention of "claude" or "AI-generated"
- [ ] Imperative mood (fix, add, not fixed, added)
- [ ] Proper capitalization and punctuation

## 🎯 Commit Execution Workflow

### **Interactive Commit Process**

1. **Present Analysis**

   - Show categorized changes
   - Suggest staging strategy
   - Recommend commit structure

2. **Staging Confirmation**

   ```bash
   # Show what will be staged
   git diff --cached --name-only

   # Execute staging
   git add [recommended-files]
   ```

3. **Message Approval**

   - Display generated commit message
   - Allow modifications and refinements
   - Confirm message meets standards

4. **Commit Execution**

   ```bash
   # Create the commit
   git commit -m "type(scope): description" -m "optional body"

   # Verify commit was created
   git log --oneline -1
   git show --stat HEAD
   ```

5. **Post-Commit Options**
   - Push to remote branch
   - Continue with more commits
   - Create pull request
   - Run tests to verify changes

## 📊 Commit Summary Report

After successful commit, provide:

### **Commit Details**

- **Hash**: [Generated commit hash]
- **Message**: [Final commit message used]
- **Files Changed**: [List of modified files with change counts]
- **Change Type**: [Primary category of changes]

### **Repository State**

- **Branch**: [Current working branch]
- **Commits Ahead**: [Number of commits ahead of main]
- **Remaining Changes**: [Any unstaged/uncommitted changes]

### **Next Actions**

- **Immediate**: [Suggested next steps]
- **Testing**: [Recommended validation steps]
- **Integration**: [Push/PR recommendations]

---

## 💡 Best Practices Reminders

### **Commit Frequency**

- Commit **early and often** with logical units
- Prefer **multiple small commits** over large ones
- Each commit should be **independently reviewable**

### **Message Quality**

- Write for **future maintainers** (including yourself)
- Be **specific enough** to understand change context
- Avoid **generic messages** like "updates" or "fixes"

### **Testing Integration**

- Run **tests before committing** when possible
- Include **test updates** with feature commits
- Consider **test-driven development** workflow

Ready to create professional, well-structured commits! 🚀

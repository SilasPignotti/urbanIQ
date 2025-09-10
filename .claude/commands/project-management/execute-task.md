---
description: "Plan and execute small development tasks with user confirmation"
---

# ⚡ Execute Quick Task

**Context Files**: Please read CLAUDE.md and CHANGELOG.md first.

Plan and execute small development tasks efficiently with detailed planning and user confirmation.

## 📝 Task Description

**Task:** $ARGUMENTS

---

## 📖 Context Loading - CRITICAL

**STEP 1 - ALWAYS FIRST**: Read CLAUDE.md completely for project understanding
**STEP 2**: Check relevant docs in ai-doc/ (if needed)
**STEP 3**: Review CHANGELOG.md for recent changes

## 🧠 Planning Phase

**THINK HARD** about this task before proceeding. Create a comprehensive plan.

### 1. Task Analysis

- **What needs to be done?** [Precise description]
- **Success criteria?** [How do I know it's complete]
- **Affected files?** [Which files need changes]
- **Dependencies?** [What does this depend on]

### 2. Codebase Pattern Research

- Search codebase for similar implementations
- Identify existing conventions and patterns
- Check test patterns and structure
- Note any architectural constraints

### 3. Detailed Implementation Plan

**THINK HARD**: Create step-by-step implementation plan

```
Implementation Steps:
- [ ] [Step 1] - [Specific action]
- [ ] [Step 2] - [Specific action]
- [ ] [Step 3] - [Specific action]

Files to modify/create:
- [ ] [File 1] - [What changes]
- [ ] [File 2] - [What changes]

Tests to write/update:
- [ ] [Test 1] - [What to test]
- [ ] [Test 2] - [What to test]

Validation steps:
- [ ] [Validation 1] - [How to verify]
- [ ] [Validation 2] - [How to verify]
```

## ⏸️ User Confirmation Required

**STOP HERE** - Present the detailed plan above to the user for confirmation before proceeding with implementation.

Ask: "Does this plan look correct? Should I proceed with implementation or would you like me to adjust anything?"

## 🚀 Implementation Phase

**Only proceed after user confirmation of the plan above.**

### Execute Implementation Steps

1. **Follow CLAUDE.md coding standards**
2. **Use existing patterns from codebase**
3. **Implement incrementally with tests**
4. **Test each step before proceeding**

### Validation Process

```bash
# Standard Quality Checks
uv run pytest src/ -v
uv run ruff check src/
uv run mypy src/
uv run ruff format src/

# Task-specific validation
[Execute the specific validation steps from plan]
```

## ✅ Success Verification

### Task Completion Check

- [ ] Task completed as defined
- [ ] All tests pass
- [ ] Code follows project standards
- [ ] No breaking changes introduced
- [ ] Integration with existing code works
- [ ] Ready for commit

### Quality Assurance

- [ ] Follows existing codebase patterns
- [ ] Proper error handling implemented
- [ ] Appropriate logging added
- [ ] Code is self-documenting
- [ ] No code duplication without good reason

## 🚫 Anti-Patterns to Avoid

- ❌ Don't ignore existing patterns
- ❌ Don't skip tests
- ❌ Don't duplicate code without good reason
- ❌ Don't implement quick/sloppy solutions
- ❌ Don't break existing functionality

## 📋 Final Report

**Implementation Summary:**

1. **Task completed**: [What was implemented]
2. **Files modified**: [List of changed files]
3. **Tests status**: [Validation results]
4. **Integration points**: [How it connects to existing code]
5. **Notes**: [Special considerations/TODOs]

**Remember**: Even small tasks should be implemented cleanly and be testable!

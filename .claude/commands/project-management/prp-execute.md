---
description: "Execute PRP implementation with comprehensive planning and validation"
---

# ⚡ Execute PRP

**Context Files**: Please read CLAUDE.md and CHANGELOG.md first.

Transform PRP into working code through systematic planning and implementation.

## 📝 PRP File

**PRP:** $ARGUMENTS

---

## 📖 Context Loading - CRITICAL

**STEP 1 - ALWAYS FIRST**: Read CLAUDE.md completely for project understanding
**STEP 2**: Read the specified PRP file completely
**STEP 3**: Read all docs referenced in the PRP from ai-doc/
**STEP 4**: Check CHANGELOG.md for recent changes

## 🧠 Implementation Planning Phase

**ULTRATHINK** through the PRP before implementation. Deep analysis of the plan leads to successful execution.

### 1. PRP Analysis

1. **Load PRP file**: Read the specified PRP file from `PRP/` directory
2. **Understand context**: Read all referenced files and documentation
3. **Understand success criteria**: What exactly needs to be achieved?
4. **Analyze existing code**: Find similar patterns in codebase

### 2. Implementation Strategy Planning

**ULTRATHINK**: Create comprehensive implementation plan

```
Implementation Analysis:
- [ ] PRP success criteria understood: [list key criteria]
- [ ] Files to modify/create: [specific file paths]
- [ ] Dependencies identified: [what this depends on]
- [ ] Integration points: [how it connects to existing code]
- [ ] Test approach: [what tests to write/update]
- [ ] Validation strategy: [how to verify success]

Implementation Steps:
- [ ] [Step 1] - [Specific action with file/function names]
- [ ] [Step 2] - [Specific action with file/function names]
- [ ] [Step 3] - [Specific action with file/function names]
- [ ] [Step 4] - [Specific action with file/function names]

Risk Assessment:
- [ ] Potential breaking changes: [list]
- [ ] Integration challenges: [list]
- [ ] Testing challenges: [list]
```

## ⏸️ User Confirmation Required

**STOP HERE** - Present the implementation analysis and plan above to the user.

Ask: "Does this implementation plan look comprehensive and correct? Should I proceed with implementation or would you like me to adjust the approach?"

## 🚀 Implementation Phase

**Only proceed after user confirmation of the plan above.**

### Execute Implementation Steps

1. **Follow CLAUDE.md coding standards**
2. **Use existing patterns from codebase**
3. **Implement step-by-step as planned**
4. **Test each step before proceeding**
5. **Follow PRP specifications exactly**

### Progressive Validation (as defined in PRP)

```bash
# Standard Quality Checks
uv run pytest src/ -v
uv run ruff check src/
uv run mypy src/
uv run ruff format src/
```

### PRP-Specific Testing

[Execute the manual tests defined in the PRP]

## ✅ Success Criteria Verification

Go through each Success Criterion from the PRP and validate:

- [ ] All tests pass
- [ ] Feature works as expected
- [ ] Code follows project standards
- [ ] Integration with existing services works
- [ ] Documentation is current
- [ ] All PRP requirements met

## 🏁 Completion Phase

### Code Quality Verification

- [ ] Follows existing codebase patterns
- [ ] Naming conventions adhered to
- [ ] No code duplication without good reason
- [ ] Error handling implemented
- [ ] Appropriate logging added

### Final Validation Checklist

- [ ] All PRP success criteria fulfilled
- [ ] Manual tests successful
- [ ] Anti-patterns avoided
- [ ] Integration points working
- [ ] Ready for commit

### Anti-Patterns to Avoid

- ❌ Don't ignore existing patterns
- ❌ Don't skip tests
- ❌ Don't duplicate code without good reason
- ❌ Don't implement quick/sloppy solutions
- ❌ Don't break existing functionality

## 📋 Implementation Report

**Final Report:**

1. **Implementation completed**: [What was implemented]
2. **Files modified/created**: [List of changed files]
3. **Test results**: [Validation status]
4. **Integration verification**: [How it connects to existing code]
5. **Remaining TODOs**: [If any]

**Remember**: Quality over speed - better to implement thoroughly than quickly and poorly.

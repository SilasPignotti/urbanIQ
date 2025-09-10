---
description: "Create focused PRP for uni-project features with comprehensive planning"
---

# 📋 Create Simple PRP

**Context Files**: Please read CLAUDE.md, CHANGELOG.md, and PRP/templates/prp_simple.md first.

Create a structured PRP for **successful one-pass implementation** with focused research.

## 📝 Feature Description

**Feature:** $ARGUMENTS

---

## 📖 Context Loading - CRITICAL

**STEP 1 - ALWAYS FIRST**: Read CLAUDE.md completely for project understanding
**STEP 2**: Check CHANGELOG.md for recent changes
**STEP 3**: Identify relevant docs in ai-doc/ (e.g., SERVICE_ARCHITECTURE.md, API_DESIGN.md)

## 🧠 Research Process (Focused)

**ULTRATHINK** through this feature before creating the PRP. Deep analysis leads to better implementation success.

### 1. Project Context Understanding

- Read CLAUDE.md completely - understand project goals and architecture
- Check CHANGELOG.md for recent changes and current state
- Identify relevant documentation in ai-doc/ directory
- Understand how this feature fits into overall system architecture

### 2. Codebase Pattern Analysis

- Search for similar features/patterns in existing codebase
- Identify files that need to be modified/created
- Check existing test patterns and structure
- Review naming conventions and architectural patterns
- Note integration points with existing services

### 3. External Research (If Needed)

- For complex topics: Create .md in ai-doc/ with relevant information
- Document important URLs and best practices
- Focus on practical implementation, not theoretical depth
- Gather implementation examples and common pitfalls

### 4. Feature Scope Definition

**ULTRATHINK**: Define precise scope and boundaries

- What exactly needs to be built?
- What are the dependencies?
- What are the integration points?
- What could go wrong during implementation?

## 📋 PRP Planning Phase

**ULTRATHINK**: Create a comprehensive plan for the PRP before writing it.

### PRP Structure Plan

```
PRP Outline:
- [ ] Title and clear goal definition
- [ ] Context reading section (which docs are relevant?)
- [ ] User persona and use case (if applicable)
- [ ] Success criteria (measurable)
- [ ] Technical details and implementation approach
- [ ] Files to modify/create
- [ ] Dependencies and integration points
- [ ] Validation steps and testing approach
- [ ] Anti-patterns to avoid
```

### Context Completeness Check

**Test**: "Would another developer have everything needed for successful implementation with this PRP?"

### Research Summary

```
Key Findings:
- [ ] Similar patterns found in: [files/locations]
- [ ] Dependencies identified: [list]
- [ ] Integration points: [list]
- [ ] Test patterns to follow: [approach]
- [ ] Potential challenges: [list]
```

## ⏸️ User Confirmation Required

**STOP HERE** - Present the PRP outline and research summary above to the user for confirmation.

Ask: "Does this PRP plan look comprehensive? Should I proceed with creating the full PRP or would you like me to research anything else first?"

## 📝 PRP Generation Phase

**Only proceed after user confirmation of the plan above.**

### Template Usage

Use `PRP/templates/prp_simple.md` as the foundation structure.

### PRP Creation Steps

1. **Filename**: `PRP/[feature-name]-[date].md`
2. **Clear title formulation**
3. **Context-reading section** - specify which docs are relevant
4. **Precise goal definition**
5. **Measurable success criteria**
6. **List all relevant files/references**
7. **Define validation approach**

## ✅ Final PRP Quality Check

### Completeness Checklist

- [ ] CLAUDE.md listed as first reference
- [ ] Relevant ai-doc/ files identified
- [ ] Similar features in code referenced
- [ ] Success criteria are testable
- [ ] Validation steps defined
- [ ] Anti-patterns mentioned
- [ ] PRP is self-contained for implementation

### Integration Validation

- [ ] Fits with existing architecture
- [ ] Follows project conventions
- [ ] Dependencies clearly stated
- [ ] Integration points defined

## 📋 Final Output

Create the final PRP as `.md` file in `PRP/` directory with structured content based on the simple template.

**Remember**: Quality over quantity - focused, actionable PRPs are better than over-complex analysis.

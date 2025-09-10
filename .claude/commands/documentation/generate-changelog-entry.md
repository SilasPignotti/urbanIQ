---
description: "Analyze conversation and create comprehensive changelog entry"
---

# Update CHANGELOG

**Context Files**: Please read CHANGELOG.md first.

Please analyze the entire conversation and create a comprehensive changelog entry in the CHANGELOG.md file. Follow these requirements:

## Analysis Requirements

1. **Review the complete conversation** from start to finish
2. **Identify all changes made** including:

   - Files created, modified, or deleted
   - Code changes and implementations
   - Configuration updates
   - Documentation changes
   - Tool installations or setup changes
   - Bug fixes and improvements

3. **Capture the context and purpose** of changes:
   - What problem was being solved?
   - What feature was being implemented?
   - What improvements were made?

## Changelog Format

Add a new entry to CHANGELOG.md using this exact format:

```markdown
## [Date: YYYY-MM-DD] - [Brief Summary Title]

### Context

- Brief description of what was accomplished in this session
- Main objectives and goals addressed

### Changes Made

#### Added

- List new files, features, or functionality added
- Include file paths where relevant

#### Modified

- List files that were changed with brief description of changes
- Include configuration or setup modifications

#### Fixed

- Bug fixes or error corrections made
- Issues resolved

#### Removed

- Any files, code, or features removed
- Deprecated functionality

### Technical Details

- Key implementation decisions made
- Important code patterns or architectures introduced
- Dependencies or tools added/configured

### Next Steps

- Any remaining tasks or follow-up work identified
- Suggestions for future improvements
- Known issues or limitations

---
```

## Instructions

1. **Read the existing CHANGELOG.md** to understand the current format and avoid duplication
2. **Create a new entry at the top** of the file (after any title/header)
3. **Use today's date** in YYYY-MM-DD format
4. **Write a concise but descriptive summary title** (max 60 characters)
5. **Fill each section comprehensively** but keep entries concise and actionable
6. **Use consistent formatting** with proper markdown syntax
7. **Include file paths** where relevant for traceability
8. **Focus on business value and technical impact** rather than just listing files

## Quality Checklist

Before finalizing, ensure:

- [ ] All significant changes from the conversation are captured
- [ ] Technical decisions and reasoning are documented
- [ ] File paths and specific changes are clearly identified
- [ ] The entry provides enough context for someone else to continue the work
- [ ] Language is professional, clear, and concise
- [ ] Formatting follows the established pattern consistently

Execute this command to create a comprehensive project documentation update that enables seamless project continuation.

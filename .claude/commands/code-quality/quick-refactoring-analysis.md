---
description: "Quick Python code analysis for immediate refactoring opportunities"
---

# Simple Refactoring Check

**Context Files**: Please read pyproject.toml, requirements.txt, and src/\*_/_.py first.

Perform a focused Python code analysis to identify immediate refactoring opportunities that improve code quality and maintainability.

## 🎯 Analysis Focus Areas

### **Code Structure & Complexity**

- Functions exceeding 20 lines requiring decomposition
- Files with excessive length (>300 lines) needing modularization
- Classes violating Single Responsibility Principle
- Deeply nested code blocks (>3 levels)

### **Architecture & Design**

- **Vertical Slice Boundaries**: Cross-feature imports violating clean architecture
- **Type Safety**: Missing Pydantic v2 models for I/O operations
- **Type Hints**: Missing or incomplete type annotations
- **Dependency Management**: Circular imports and tight coupling

### **Code Quality Indicators**

- Duplicate code patterns
- Magic numbers and hardcoded values
- Long parameter lists (>4 parameters)
- Complex conditional logic

## 📋 Desired Architecture Principles

- ✅ **Vertical Slice Architecture**: Clear feature boundaries
- ✅ **Single Responsibility**: One reason to change per module/class
- ✅ **Type Safety**: Comprehensive Pydantic v2 models
- ✅ **Clean Interfaces**: Well-defined input/output contracts

## 📊 Issue Reporting Format

For each identified issue, provide:

### **Issue Template**

```
🔍 **Issue**: [Brief description]
📍 **Location**: `file_path:line_number`
⚠️  **Problem**: [Why this is problematic]
🔧 **Solution**: [Specific fix with code example]
📂 **Implementation**: [Exact location for the fix]
🚨 **Priority**: [High/Medium/Low]
⏱️  **Effort**: [Estimated time to fix]
```

## 🎯 Execution Guidelines

1. **Scan systematically** through the codebase
2. **Prioritize quick wins** that can be fixed in <1 hour each
3. **Focus on actionable items** with clear implementation steps
4. **Group related issues** for batch processing
5. **Highlight high-impact/low-effort** improvements first

## 🚀 Output Structure

### **Executive Summary**

- Total issues found by category
- Recommended fix order
- Estimated total refactoring time

### **Detailed Analysis**

- Issues grouped by priority
- Code examples for each fix
- Implementation roadmap

Begin the analysis by scanning the current codebase for the specified patterns and architectural violations.

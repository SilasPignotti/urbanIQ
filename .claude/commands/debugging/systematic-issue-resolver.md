---
description: "Systematic debugging and issue diagnosis with root cause analysis"
---

# 🔍 Smart Debugger

**Context Files**: Please read \*.log, package.json, pyproject.toml, and .env.example first.

Systematically debug and diagnose issues using structured problem-solving methodology.

## 📝 Problem Description

**Issue Details:** $ARGUMENTS

---

## 🛠️ Systematic Debugging Process

### **Phase 1: 🎯 Issue Reproduction**

- [ ] **Exact Steps**: Document precise reproduction steps
- [ ] **Environment Check**: Verify same environment conditions
- [ ] **Error Capture**: Record all error messages and stack traces
- [ ] **Behavior Analysis**: Expected vs. actual behavior documentation
- [ ] **Consistency Test**: Reproduce multiple times to confirm pattern

### **Phase 2: 📊 Information Gathering**

#### **Code History Analysis**

```bash
# Recent changes that might be related
git log --oneline --since="1 week ago" --grep="relevant_keyword"

# Check blame for problematic lines
git blame path/to/file.py

# Find when issue was introduced
git bisect start
```

#### **System State Investigation**

- 🔍 **Logs Review**: Application, system, and error logs
- 🌐 **Environment Variables**: Configuration and secrets validation
- 📦 **Dependencies**: Version conflicts and compatibility issues
- 🗄️ **Database State**: Data integrity and schema validation

### **Phase 3: 🎯 Problem Isolation**

#### **Debugging Techniques by Issue Type**

##### **🚨 Runtime Errors**

- ✅ **Stack Trace Analysis**: Full error chain examination
- ✅ **Variable Inspection**: Values and types at failure point
- ✅ **Memory Usage**: Resource consumption patterns
- ✅ **Exception Handling**: Proper error propagation

##### **🔄 Logic Errors**

- ✅ **Execution Tracing**: Step-by-step flow analysis
- ✅ **Boundary Testing**: Edge cases and limits
- ✅ **State Verification**: Data consistency at each step
- ✅ **Minimal Examples**: Isolated test cases

##### **⚡ Performance Issues**

- ✅ **Profiling**: CPU, memory, and I/O bottlenecks
- ✅ **Query Analysis**: Database performance and N+1 problems
- ✅ **Algorithm Review**: Big O complexity assessment
- ✅ **Caching Strategy**: Hit rates and invalidation

##### **🔗 Integration Issues**

- ✅ **Service Connectivity**: Network and endpoint availability
- ✅ **Authentication**: Credentials and permissions validation
- ✅ **Data Format**: Request/response schema compliance
- ✅ **API Testing**: Isolated service validation

### **Phase 4: 🔬 Root Cause Analysis**

#### **The 5 Whys Technique**

1. **Why** did the issue occur?
2. **Why** wasn't it detected earlier?
3. **Why** are similar issues possible?
4. **Why** don't current safeguards prevent this?
5. **Why** is the system vulnerable to this class of problems?

#### **Impact Assessment**

- 📈 **Scope**: How widespread is the issue?
- ⏰ **Timeline**: When did it start occurring?
- 👥 **Users Affected**: Who is experiencing the problem?
- 💼 **Business Impact**: Revenue, operations, or reputation effects

### **Phase 5: 🔧 Solution Implementation**

#### **Fix Strategy**

- 🎯 **Root Cause Fix**: Address underlying problem, not symptoms
- 🛡️ **Defensive Programming**: Add validation and error handling
- ⚖️ **Minimal Change Principle**: KISS - Keep It Simple, Stupid
- 🧪 **Edge Case Coverage**: Handle boundary conditions

#### **Implementation Checklist**

- [ ] Fix addresses root cause
- [ ] Code follows project patterns
- [ ] Error handling improved
- [ ] Edge cases considered
- [ ] Performance impact assessed

### **Phase 6: ✅ Solution Verification**

#### **Testing Strategy**

- 🔄 **Original Issue**: Confirm fix resolves reported problem
- 🔍 **Regression Testing**: Ensure no new issues introduced
- 🎯 **Related Functionality**: Test connected features
- 📋 **Test Case Addition**: Prevent future occurrences

#### **Validation Checklist**

- [ ] Issue resolved in all environments
- [ ] No performance regression
- [ ] All existing tests pass
- [ ] New tests added for bug scenario
- [ ] Documentation updated if needed

### **Phase 7: 📋 Documentation & Learning**

#### **Debug Summary Template**

```markdown
## 🐛 Debug Report

### **Issue Overview**

- **Problem**: [Concise description of what was broken]
- **Severity**: [Critical/High/Medium/Low]
- **Affected Components**: [Systems/features impacted]

### **Root Cause**

- **Technical Cause**: [Why it was broken - technical details]
- **Process Cause**: [How it got through - process failure]
- **Timeline**: [When issue started and was discovered]

### **Solution Implemented**

- **Fix Description**: [What was changed]
- **Files Modified**: [List of changed files]
- **Testing Strategy**: [How fix was validated]

### **Prevention Measures**

- **Immediate**: [Quick safeguards added]
- **Short-term**: [Process improvements]
- **Long-term**: [Systemic changes to prevent similar issues]

### **Lessons Learned**

- [Key insights for future debugging]
- [Process improvements identified]
- [Team knowledge gained]
```

---

## 🎯 Final Debug Checklist

### **Resolution Verification**

- [ ] Original issue reproduced and confirmed fixed
- [ ] Root cause identified and documented
- [ ] Fix implemented following best practices
- [ ] Comprehensive tests added/updated
- [ ] No regressions introduced in related functionality
- [ ] Performance impact assessed and acceptable
- [ ] Documentation updated where necessary

### **Knowledge Transfer**

- [ ] Debug findings shared with team
- [ ] Process improvements identified
- [ ] Similar vulnerability patterns documented
- [ ] Monitoring/alerting enhanced if needed

---

## 💡 Remember

> **The goal is not just to fix the bug, but to understand why it happened and build systems that prevent similar issues in the future.**

**Debugging Philosophy**: Every bug is a learning opportunity and a chance to strengthen the system's resilience. 🚀

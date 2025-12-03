# Code Review Command

Review the specified file or changes for security issues, code quality, and best practices.

## Usage

```
/review [file-path]
/review --staged    # Review staged git changes
/review --pr        # Review current PR changes
```

## Review Process

1. **Security Check**
   - Input validation
   - SQL injection risks
   - XSS vulnerabilities
   - Hardcoded secrets

2. **Code Quality**
   - Function complexity
   - Error handling
   - Naming conventions
   - Code duplication

3. **Best Practices**
   - Project conventions
   - Test coverage
   - Documentation

## Output

Provide a structured review with:
- 🔴 Critical issues (must fix)
- 🟡 Warnings (should fix)
- 🟢 Suggestions (nice to have)
- ✅ What's good

Reference @.claude/Agents/code-reviewer.md for detailed review guidelines.

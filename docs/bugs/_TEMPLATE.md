# Bug Analysis: [Brief Bug Title]

> **Date Discovered:** YYYY-MM-DD
> **Date Fixed:** YYYY-MM-DD (or "In Progress")
> **Severity:** [Critical | High | Medium | Low]
> **Status:** [Open | In Progress | Fixed | Won't Fix]

## Summary

[1-2 sentence description of the bug]

## Symptoms

- [What the user sees/experiences]
- [Error messages if any]
- [When it occurs]

## Steps to Reproduce

1. [Step 1]
2. [Step 2]
3. [Step 3]
4. Expected: [What should happen]
5. Actual: [What actually happens]

## Environment

- **Browser/Device:** [e.g., Chrome 120]
- **OS:** [e.g., Windows 11]
- **FormAI Version:** [e.g., 1.0.0]
- **Python Version:** [e.g., 3.11]

## Root Cause Analysis

### Investigation

[Describe the investigation process and findings]

### Root Cause

**Location:** `path/to/file.py` Line [X]

**The Problem:**
```python
# Current (broken) code
```

**Why This Breaks:**
[Explanation of why this code causes the bug]

## The Fix

### Solution

**File:** `path/to/file.py`

**Change:**
```python
# FROM (broken):
old_code()

# TO (fixed):
new_code()
```

### Why This Fix Works

[Explanation of why the fix resolves the issue]

## Testing

### Verification Steps

- [ ] Bug no longer reproducible
- [ ] No regression in related features
- [ ] Works across different scenarios
- [ ] Edge cases handled

### Test Cases Added

- [ ] Unit test: `tests/test_feature.py`
- [ ] Integration test: `tests/integration/test_feature.py`

## Impact Assessment

### Affected Users
- [Who was affected]
- [How many users approximately]

### Related Code
- `file1.py` - [How it's related]
- `file2.py` - [How it's related]

## Prevention

### How to Prevent Similar Bugs

- [Recommendation 1]
- [Recommendation 2]

### Code Review Checklist Addition

- [ ] [New check to add to code review process]

## Files Changed

| File | Change |
|------|--------|
| `path/to/file.py` | Fixed X logic |
| `tests/test_file.py` | Added test for bug |

## Related Issues

- GitHub Issue: #[number]
- Related Bug: [link]

## Timeline

| Date | Event |
|------|-------|
| YYYY-MM-DD | Bug reported |
| YYYY-MM-DD | Root cause identified |
| YYYY-MM-DD | Fix implemented |
| YYYY-MM-DD | Fix deployed |

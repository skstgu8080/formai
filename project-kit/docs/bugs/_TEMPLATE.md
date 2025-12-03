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

- **Browser/Device:** [e.g., Chrome 120, iPhone 15]
- **OS:** [e.g., Windows 11, macOS Sonoma]
- **App Version:** [e.g., 1.2.3]
- **User Role:** [e.g., Admin, Regular User]

## Root Cause Analysis

### Investigation

[Describe the investigation process and findings]

### Root Cause

**Location:** `path/to/file.ts` Line [X]

**The Problem:**
```typescript
// Current (broken) code
```

**Why This Breaks:**
[Explanation of why this code causes the bug]

## The Fix

### Solution

**File:** `path/to/file.ts`

**Change:**
```typescript
// FROM (broken):
oldCode();

// TO (fixed):
newCode();
```

### Why This Fix Works

[Explanation of why the fix resolves the issue]

## Testing

### Verification Steps

- [ ] Bug no longer reproducible
- [ ] No regression in related features
- [ ] Works across browsers/devices
- [ ] Edge cases handled

### Test Cases Added

- [ ] Unit test: `tests/feature.test.ts`
- [ ] Integration test: `tests/integration/feature.test.ts`

## Impact Assessment

### Affected Users
- [Who was affected]
- [How many users approximately]

### Related Code
- `file1.ts` - [How it's related]
- `file2.ts` - [How it's related]

## Prevention

### How to Prevent Similar Bugs

- [Recommendation 1]
- [Recommendation 2]

### Code Review Checklist Addition

- [ ] [New check to add to code review process]

## Files Changed

| File | Change |
|------|--------|
| `path/to/file.ts` | Fixed X logic |
| `path/to/test.ts` | Added test for bug |

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

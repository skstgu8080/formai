# Testing Requirements

## Testing Workflow Rules

### General Principles

1. **Tests are mandatory** - Every feature/bugfix must have tests
2. **Code is never "done" without tests** - All tests must pass before completion
3. **Coverage requirements:**
   - Minimum **80%** for new code
   - Critical paths (auth, payments, validation) require **90%+**

---

## Test-First Thinking

Before writing code, create a **Test Plan**:

```
Test Plan:
- Test case 1: [normal behavior]
- Test case 2: [edge case]
- Test case 3: [failure/recovery scenario]
- Regression tests: [existing behavior to preserve]
```

---

## Writing Real Tests (No Fake "Green")

### Rules
- Tests MUST reflect reality and be capable of failing
- NEVER write tests that only assert constants or always-true conditions
- Mocks should only mock external dependencies, not the system under test
- Test names must clearly state WHAT is tested, under WHICH conditions, WHAT outcome is expected

### Bad Test (Fake Green)
```javascript
// ❌ BAD - Doesn't test real behavior
test('user login works', () => {
  const result = { success: true };
  expect(result.success).toBe(true);
});
```

### Good Test
```javascript
// ✅ GOOD - Tests actual login logic
test('user login succeeds with valid credentials', async () => {
  const result = await login('user@example.com', 'correctPassword');
  expect(result.success).toBe(true);
  expect(result.user).toBeDefined();
  expect(result.token).toBeDefined();
});
```

---

## Test Types

### Unit Tests (~70% of tests)
- Test individual functions in isolation
- Fast (< 100ms each)
- Mock external dependencies
- Test one thing at a time

### Integration Tests (~25% of tests)
- Test how components work together
- API endpoints, database operations
- May use test database
- Slower (< 1s each)

### E2E Tests (~5% of tests)
- Test complete user workflows
- Critical paths only (signup → login → purchase)
- Slowest (several seconds)

---

## Coverage Thresholds

| Code Type | Minimum Coverage |
|-----------|------------------|
| New code | 80% |
| Critical paths | 90%+ |
| Utility functions | 95%+ |
| UI components | 70%+ |

---

## Edge Cases to Test

### Input Validation
- Empty inputs (`''`, `null`, `undefined`, `[]`, `{}`)
- Invalid data types
- Boundary values (min/max, 0, negative)
- Special characters
- Very long inputs

### Error Handling
- Network failures
- Database errors
- Authentication failures
- Authorization failures
- Rate limiting

---

## Definition of "Done"

A task is complete when:

- [ ] Requested behavior is implemented
- [ ] Test Plan was documented
- [ ] Tests cover new behavior, edge cases, errors
- [ ] Tests are real (would fail if code is broken)
- [ ] All tests pass
- [ ] Coverage meets threshold (80%+ for new code)
- [ ] No regressions

---

## Commands Template

Update these for your project:

```bash
# Run tests
[YOUR_TEST_COMMAND]        # e.g., npm test, pytest, go test

# Run with coverage
[YOUR_COVERAGE_COMMAND]    # e.g., npm run test:coverage

# Run specific test
[YOUR_SINGLE_TEST_COMMAND] # e.g., npm test -- --grep "test name"
```

# Testing Requirements

## Testing Workflow Rules

### General Principles

1. **Tests validate real behavior** - Every feature/bugfix should have tests
2. **Code is never "done" without tests** - All tests must pass before completion
3. **Coverage requirements:**
   - Minimum **80%** for new code
   - Critical paths (automation, API endpoints) require **90%+**

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
- Mocks should only mock external dependencies (browser, AI APIs), not the system under test
- Test names must clearly state WHAT is tested, under WHICH conditions, WHAT outcome is expected

### Bad Test (Fake Green)
```python
# BAD - Doesn't test real behavior
def test_profile_works():
    result = {"success": True}
    assert result["success"] == True
```

### Good Test
```python
# GOOD - Tests actual profile creation
def test_create_profile_with_valid_data():
    profile_data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    response = client.post("/api/profiles", json=profile_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"
```

---

## Test Types for FormAI

### Unit Tests (~70% of tests)
Test individual functions in isolation:
- Profile normalization logic
- Field mapping algorithms
- Data validation functions
- Utility functions

**Location:** `tests/unit/`

```python
# Example: Test profile normalization
def test_normalize_nested_profile():
    nested = {"personal": {"firstName": "John", "lastName": "Doe"}}
    flat = normalize_profile(nested)
    assert flat["firstName"] == "John"
```

### Integration Tests (~25% of tests)
Test how components work together:
- API endpoint responses
- File read/write operations
- WebSocket communication

**Location:** `tests/integration/`

```python
# Example: Test API endpoint
def test_get_profiles_endpoint():
    response = client.get("/api/profiles")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Automation Tests (~5% of tests)
Test browser automation flows:
- Recording import and parsing
- Field detection
- Form filling (with mock browser)

**Location:** `tests/automation/`

```python
# Example: Test recording parser
def test_parse_chrome_recording():
    recording = load_test_recording("sample.json")
    steps = parse_chrome_recording(recording)
    assert len(steps) > 0
    assert steps[0]["type"] == "navigate"
```

---

## Coverage Thresholds

| Code Type | Minimum Coverage |
|-----------|------------------|
| New code | 80% |
| API endpoints | 90%+ |
| Automation logic | 90%+ |
| Utility functions | 95%+ |
| UI JavaScript | 70%+ |

---

## Edge Cases to Test

### Input Validation
- Empty inputs (`''`, `None`, `[]`, `{}`)
- Invalid data types
- Boundary values (very long names, special characters)
- Malformed JSON
- Invalid URLs

### File Operations
- Non-existent files
- Permission errors
- Corrupted JSON
- Very large files

### Browser Automation
- Page load failures
- Element not found
- Timeout scenarios
- Network errors

### Error Handling
- API endpoint failures
- WebSocket disconnection
- Invalid profile data
- Automation failures

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

## Test Commands

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_server.py -v

# Run specific test
pytest tests/test_server.py::test_profile_creation -v

# Run tests matching pattern
pytest tests/ -k "profile" -v

# Run with verbose output
pytest tests/ -v --tb=short
```

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_profile.py      # Profile logic tests
│   ├── test_field_mapper.py # Field mapping tests
│   └── test_utils.py        # Utility function tests
├── integration/
│   ├── test_api.py          # API endpoint tests
│   ├── test_websocket.py    # WebSocket tests
│   └── test_files.py        # File operation tests
├── automation/
│   ├── test_recording.py    # Recording tests
│   └── test_replay.py       # Replay tests
└── fixtures/
    ├── sample_profile.json  # Test profile data
    └── sample_recording.json # Test recording data
```

---

## Fixtures and Test Data

Use pytest fixtures for common test setup:

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from formai_server import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_profile():
    return {
        "id": "test-123",
        "name": "Test User",
        "email": "test@example.com"
    }
```

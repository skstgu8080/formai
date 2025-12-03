# Test Generation Command

Generate tests for the specified file or function.

## Usage

```
/test [file-path]
/test [file-path] --function [function-name]
/test [file-path] --coverage  # Focus on uncovered code
```

## Test Generation Process

1. **Analyze Code**
   - Identify function inputs and outputs
   - Find edge cases
   - Locate error conditions

2. **Generate Test Plan**
   - Normal behavior tests
   - Edge case tests
   - Error handling tests

3. **Write Tests**
   - Use project's testing framework
   - Follow testing conventions
   - Include meaningful assertions

## Test Categories

### Unit Tests
- Test single functions in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test component interactions
- May use test database
- Verify API contracts

## Output

Generate tests that:
- Cover happy path
- Handle edge cases (null, empty, boundary values)
- Test error conditions
- Follow @.claude/testing.md guidelines

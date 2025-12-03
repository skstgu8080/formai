# Feature: [Feature Name]

> **Status:** [Planning | In Progress | Completed | Deprecated]
> **Created:** YYYY-MM-DD
> **Last Updated:** YYYY-MM-DD

## Overview

[1-2 sentence description of what this feature does and why it exists]

## User Stories

- As a [user type], I want to [action] so that [benefit]
- As a [user type], I want to [action] so that [benefit]

## Architecture

### Data Changes

**New JSON Schema:**
```json
{
  "id": "string",
  "field1": "type",
  "field2": "type",
  "created_at": "timestamp"
}
```

**Modified Files:**
- `profiles/*.json`: Added `new_field`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/feature` | Get feature data |
| POST | `/api/feature` | Create new item |

### Files Modified

- `formai_server.py` - New API endpoints
- `tools/feature_module.py` - Business logic
- `web/feature.html` - UI page

## Technical Details

### Implementation Notes

[Any important technical decisions, algorithms, or approaches used]

### Dependencies

- [Package name] - [Why it's needed]

### Environment Variables

```env
FEATURE_API_KEY=        # Required for [reason]
```

## Usage

### Basic Usage

```python
# Example code showing how to use the feature
from tools.feature_module import FeatureClass

feature = FeatureClass()
result = feature.do_something()
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `option1` | bool | `True` | Description |
| `option2` | str | `'default'` | Description |

## Testing

### Unit Tests
- [ ] Test case 1
- [ ] Test case 2

### Integration Tests
- [ ] API endpoint tests
- [ ] File operations

### Manual Testing Checklist
- [ ] Feature works in dashboard
- [ ] Error states handled
- [ ] Loading states shown

## Security Considerations

- [Any security considerations for this feature]
- [Input validation requirements]

## Performance Considerations

- [Any performance considerations]
- [Caching strategies used]

## Future Enhancements

- [ ] Potential enhancement 1
- [ ] Potential enhancement 2

## Related Documentation

- [Link to related doc]
- [Link to related doc]

## Changelog

| Date | Change |
|------|--------|
| YYYY-MM-DD | Initial implementation |

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

### Database Changes

**New Tables:**
```typescript
// table_name
{
  id: string,
  field1: type,
  field2: type,
  created_at: timestamp
}
```

**Modified Tables:**
- `existing_table`: Added `new_field` column

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/feature` | Get feature data |
| POST | `/api/feature` | Create new item |

### UI Components

- `components/feature/FeatureComponent.tsx` - Main component
- `components/feature/FeatureForm.tsx` - Form for creating/editing

### Files Modified

- `src/app/dashboard/feature/page.tsx` - New page
- `src/lib/feature.ts` - Business logic
- `src/types/feature.ts` - Type definitions

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

```typescript
// Example code showing how to use the feature
import { useFeature } from '@/hooks/useFeature';

const MyComponent = () => {
  const { data, loading } = useFeature();
  // ...
};
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `option1` | boolean | `true` | Description |
| `option2` | string | `'default'` | Description |

## Testing

### Unit Tests
- [ ] Test case 1
- [ ] Test case 2

### Integration Tests
- [ ] API endpoint tests
- [ ] Database operations

### Manual Testing Checklist
- [ ] Feature works on desktop
- [ ] Feature works on mobile
- [ ] Error states handled
- [ ] Loading states shown

## Security Considerations

- [Any security considerations for this feature]
- [Authentication/authorization requirements]

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

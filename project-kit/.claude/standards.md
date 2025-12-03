# Code Quality & Standards

## General Principles

### Code Style
- Follow existing project conventions
- Use consistent formatting (Prettier, ESLint, etc.)
- Keep functions small and focused (< 50 lines ideal)
- Use descriptive names for variables and functions
- Avoid magic numbers - use named constants

### Comments
- Write self-documenting code first
- Comment the "why", not the "what"
- Keep comments up-to-date with code changes
- Remove commented-out code before committing

---

## Naming Conventions

### Variables & Functions
```javascript
// camelCase for variables and functions
const userName = 'John';
function getUserById(id) { }

// UPPER_SNAKE_CASE for constants
const MAX_RETRY_ATTEMPTS = 3;
const API_BASE_URL = 'https://api.example.com';

// PascalCase for classes and components
class UserService { }
function UserProfile() { }
```

### Files & Directories
```
# kebab-case for files
user-service.ts
api-routes.js

# PascalCase for React components
UserProfile.tsx
NavigationMenu.jsx
```

### Boolean Variables
```javascript
// Prefix with is, has, can, should
const isActive = true;
const hasPermission = false;
const canEdit = true;
const shouldRefresh = false;
```

---

## Function Guidelines

### Single Responsibility
Each function should do one thing well.

```javascript
// ❌ Bad - does too much
function processUser(user) {
  validateUser(user);
  saveToDatabase(user);
  sendEmail(user);
  logActivity(user);
}

// ✅ Good - single purpose
function saveUser(user) {
  return database.save(user);
}
```

### Pure Functions
Prefer pure functions when possible:
```javascript
// ✅ Pure - same input always gives same output
function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}
```

### Error Handling
```javascript
// Always handle errors explicitly
async function fetchUser(id) {
  try {
    const response = await api.get(`/users/${id}`);
    return response.data;
  } catch (error) {
    logger.error('Failed to fetch user', { id, error });
    throw new UserNotFoundError(id);
  }
}
```

---

## Code Organization

### Import Order
```javascript
// 1. External packages
import React from 'react';
import { useState } from 'react';

// 2. Internal modules
import { UserService } from '@/services/user';
import { Button } from '@/components/ui';

// 3. Types
import type { User } from '@/types';

// 4. Styles
import styles from './Component.module.css';
```

### File Structure
```
// Component file structure
ComponentName/
├── index.ts           # Exports
├── ComponentName.tsx  # Main component
├── ComponentName.test.tsx
├── ComponentName.module.css
└── types.ts           # Component-specific types
```

---

## Git Commit Messages

### Format
```
<type>: <description>

[optional body]

[optional footer]
```

### Types
| Type | Usage |
|------|-------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation only |
| style | Formatting, no code change |
| refactor | Code change, no new feature or fix |
| test | Adding tests |
| chore | Maintenance tasks |

### Examples
```
feat: Add user authentication with JWT

fix: Resolve race condition in cart updates

docs: Update API documentation for v2 endpoints

refactor: Extract validation logic to separate module
```

---

## Code Review Checklist

Before submitting PR:
- [ ] Code follows project conventions
- [ ] Functions are small and focused
- [ ] No commented-out code
- [ ] No console.log or debug statements
- [ ] Error handling is appropriate
- [ ] Tests are included
- [ ] No secrets or credentials
- [ ] Documentation updated if needed

---

## Performance Guidelines

### Avoid
- N+1 queries (use eager loading)
- Unnecessary re-renders (memoization)
- Blocking the main thread
- Memory leaks (clean up subscriptions)

### Optimize
- Use pagination for large datasets
- Lazy load when appropriate
- Cache expensive computations
- Use appropriate data structures

---

## Accessibility (If Applicable)

- Use semantic HTML elements
- Include alt text for images
- Ensure keyboard navigation works
- Maintain sufficient color contrast
- Test with screen readers

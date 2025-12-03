# API Design Guidelines

## REST API Conventions

### HTTP Methods

| Method | Purpose | Idempotent |
|--------|---------|------------|
| GET | Retrieve resources | Yes |
| POST | Create resources | No |
| PUT | Replace resources | Yes |
| PATCH | Partial update | Yes |
| DELETE | Remove resources | Yes |

### URL Structure

```
GET    /api/v1/users          # List users
GET    /api/v1/users/:id      # Get single user
POST   /api/v1/users          # Create user
PUT    /api/v1/users/:id      # Replace user
PATCH  /api/v1/users/:id      # Update user fields
DELETE /api/v1/users/:id      # Delete user
```

### Naming Conventions
- Use plural nouns for resources (`/users`, not `/user`)
- Use kebab-case for multi-word resources (`/user-profiles`)
- Use query params for filtering (`/users?role=admin&status=active`)
- Use nested routes sparingly (`/users/:id/posts`)

---

## Response Format

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "perPage": 20,
    "total": 100
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      { "field": "email", "message": "Invalid email format" }
    ]
  }
}
```

---

## HTTP Status Codes

### Success
| Code | Usage |
|------|-------|
| 200 | Success with response body |
| 201 | Resource created |
| 204 | Success with no content |

### Client Errors
| Code | Usage |
|------|-------|
| 400 | Bad request / validation error |
| 401 | Unauthorized (not authenticated) |
| 403 | Forbidden (not authorized) |
| 404 | Resource not found |
| 409 | Conflict (duplicate, etc.) |
| 422 | Unprocessable entity |
| 429 | Too many requests |

### Server Errors
| Code | Usage |
|------|-------|
| 500 | Internal server error |
| 502 | Bad gateway |
| 503 | Service unavailable |

---

## Pagination

Use cursor-based or offset pagination:

```
GET /api/users?page=2&perPage=20
GET /api/users?cursor=abc123&limit=20
```

Always include pagination metadata in response.

---

## Versioning

Include version in URL path:
```
/api/v1/users
/api/v2/users
```

---

## Authentication

- Use Bearer tokens in Authorization header
- Never send credentials in URL query params
- Use short-lived access tokens + refresh tokens

```
Authorization: Bearer <token>
```

---

## Rate Limiting Headers

Include in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

---

## Logging

### What to Log
- Request method, path, status code
- Response time
- User ID (if authenticated)
- Request ID for tracing
- Errors with stack traces (server-side only)

### What NOT to Log
- Passwords or tokens
- Full credit card numbers
- Personal identification numbers
- Session tokens in plain text

### Log Format (JSON)
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "requestId": "abc-123",
  "method": "POST",
  "path": "/api/users",
  "status": 201,
  "duration": 45,
  "userId": "user-456"
}
```

---

## Error Handling

### Rules
- Return consistent error format
- Include error code for programmatic handling
- Provide human-readable message
- Log detailed errors server-side
- Never expose internal details to clients

### Error Codes
Define application-specific error codes:
```
VALIDATION_ERROR
AUTHENTICATION_REQUIRED
PERMISSION_DENIED
RESOURCE_NOT_FOUND
RATE_LIMIT_EXCEEDED
INTERNAL_ERROR
```

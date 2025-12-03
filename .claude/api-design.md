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
GET    /api/profiles          # List profiles
GET    /api/profiles/{id}     # Get single profile
POST   /api/profiles          # Create profile
PUT    /api/profiles/{id}     # Replace profile
DELETE /api/profiles/{id}     # Delete profile
```

### Naming Conventions
- Use plural nouns for resources (`/profiles`, not `/profile`)
- Use kebab-case for multi-word resources (`/field-mappings`)
- Use query params for filtering (`/recordings?status=completed`)
- Use nested routes sparingly (`/recordings/{id}/replay`)

---

## Response Format

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "count": 10,
    "page": 1
  }
}
```

Or for simple responses:
```json
{
  "id": "profile-123",
  "name": "John Doe",
  "email": "john@example.com"
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
| 404 | Resource not found |
| 409 | Conflict (duplicate profile, etc.) |
| 422 | Unprocessable entity |

### Server Errors
| Code | Usage |
|------|-------|
| 500 | Internal server error |
| 503 | Service unavailable |

---

## FormAI API Reference

### Profile Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profiles` | List all profiles |
| GET | `/api/profiles/{id}` | Get specific profile |
| POST | `/api/profiles` | Create new profile |
| PUT | `/api/profiles/{id}` | Update profile |
| DELETE | `/api/profiles/{id}` | Delete profile |

### Automation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/automation/start` | Start automation job |
| POST | `/api/automation/stop` | Stop all automation |
| POST | `/api/automation/stop/{session_id}` | Stop specific session |
| GET | `/api/status` | Get server status |

### Recordings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/recordings` | List all recordings |
| GET | `/api/recordings/{id}` | Get specific recording |
| POST | `/api/recordings/import-chrome` | Import Chrome recording |
| DELETE | `/api/recordings/{id}` | Delete recording |
| POST | `/api/recordings/{id}/replay` | Replay recording |
| GET | `/api/recordings/{id}/analyze` | Analyze recording fields |

### Field Mappings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/field-mappings` | Get all mappings |
| POST | `/api/field-mappings` | Create field mapping |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `WS /ws` | Real-time automation updates |

---

## Pagination

Use offset pagination:

```
GET /api/profiles?page=2&limit=20
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "meta": {
    "page": 2,
    "limit": 20,
    "total": 100
  }
}
```

---

## WebSocket Messages

### Client to Server
```json
{
  "type": "subscribe",
  "channel": "automation"
}
```

### Server to Client
```json
{
  "type": "progress",
  "data": {
    "session_id": "abc123",
    "step": "filling_form",
    "progress": 50
  }
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
PROFILE_NOT_FOUND
RECORDING_NOT_FOUND
AUTOMATION_FAILED
BROWSER_ERROR
INTERNAL_ERROR
```

---

## Logging

### What to Log
- Request method, path, status code
- Response time
- Request ID for tracing
- Errors with stack traces (server-side only)
- Automation events

### What NOT to Log
- Profile data contents
- API keys or tokens
- Full request/response bodies (unless debugging)

### Log Format (JSON)
```json
{
  "timestamp": "2025-12-01T10:30:00Z",
  "level": "info",
  "requestId": "abc-123",
  "method": "POST",
  "path": "/api/automation/start",
  "status": 200,
  "duration": 45
}
```

---

## FastAPI Implementation Patterns

### Request Validation with Pydantic
```python
from pydantic import BaseModel, EmailStr

class ProfileCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None

@app.post("/api/profiles")
async def create_profile(profile: ProfileCreate):
    # Pydantic automatically validates
    ...
```

### Error Responses
```python
from fastapi import HTTPException

@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    profile = load_profile(profile_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"}
        )
    return profile
```

### Response Models
```python
from pydantic import BaseModel

class ProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str

@app.get("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    ...
```

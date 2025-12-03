# Security Guidelines

> **Based on OWASP Application Security Verification Standard (ASVS)**
> **Adapted for Python/FastAPI + Browser Automation**

## Quick Reference - Critical Security Rules

### ALWAYS
- Use Pydantic models for all request validation
- Sanitize all user input before processing
- Store API keys in environment variables, never in code
- Use HTTPS in production
- Return generic error messages to users
- Log security events with proper metadata
- Validate file paths to prevent directory traversal
- Use parameterized queries if database is added

### NEVER
- Store passwords, API keys, or secrets in plain text or JSON files
- Expose stack traces or internal errors to users
- Commit secrets to version control
- Trust client-side validation alone
- Execute user input as code or commands
- Store sensitive profile data unencrypted

---

## Input Validation & Sanitization

### Request Validation
- **Use Pydantic models** for all API request bodies
- **Validate file uploads** - check MIME type, size limits, and sanitize filenames
- **Validate URLs** - ensure they're well-formed before browser navigation
- **Sanitize profile data** - escape HTML/JS in text fields

### Path Traversal Prevention
```python
# ALWAYS validate file paths
import os

def safe_path(base_dir: str, filename: str) -> str:
    """Prevent directory traversal attacks."""
    full_path = os.path.abspath(os.path.join(base_dir, filename))
    if not full_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("Invalid file path")
    return full_path
```

### URL Validation
```python
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """Ensure URL is safe for browser navigation."""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    if not parsed.netloc:
        return False
    return True
```

---

## API Key & Secrets Management

### Environment Variables
- Store all API keys in `.env` file (gitignored)
- Never hardcode keys in Python files
- Validate required keys at startup

### API Key Patterns
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Validate at startup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable required")
```

### Secrets to Protect
- OpenAI/OpenRouter API keys
- Admin server credentials
- Any authentication tokens

---

## Profile Data Security

### Sensitive Fields
Profile data may contain:
- Names, addresses, phone numbers
- Email addresses
- Financial information
- SSN or ID numbers

### Protection Guidelines
- Store profiles with restricted file permissions
- Consider encrypting sensitive fields at rest
- Never log profile data contents
- Sanitize profile data before displaying in UI

---

## Browser Automation Security

### SeleniumBase/Playwright
- Use UC mode for stealth but understand its risks
- Validate URLs before navigation
- Don't execute arbitrary JavaScript from user input
- Clean up browser sessions properly
- Don't save cookies/sessions with sensitive data

### Recording Security
- Sanitize recordings before storage
- Remove any captured credentials from recordings
- Don't replay recordings on unvalidated URLs

---

## HTTP Security Headers

Set these headers on all responses:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

## CORS Configuration

```python
# Development - more permissive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5511"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Production - restrict to known origins
# NEVER use allow_origins=["*"] in production
```

---

## Rate Limiting

Recommended limits for FormAI:

| Endpoint | Limit |
|----------|-------|
| Automation start | 10 / minute |
| Profile create | 30 / hour |
| Recording import | 20 / hour |
| API general | 100 / minute |

---

## Error Handling & Logging

### Error Messages
- Return generic messages to users ("Operation failed", not "File /etc/passwd not found")
- Log detailed errors server-side with `exc_info=True`
- Never expose stack traces to API responses

### Security Event Logging
Log these events with timestamp, IP address, and context:
- Failed API requests
- Invalid file access attempts
- Automation errors
- Configuration changes

---

## Admin Callback Security

When using admin callback system:
- Use HTTPS for admin server communication
- Validate admin server SSL certificate
- Don't send sensitive profile data in heartbeats
- Authenticate command execution

---

## Security Checklist

Before deploying, verify:

- [ ] API keys in environment variables
- [ ] `.env` file in `.gitignore`
- [ ] Input validation on all endpoints
- [ ] File path validation (no traversal)
- [ ] URL validation before navigation
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Error messages are generic
- [ ] Security events are logged
- [ ] Profile data access restricted
- [ ] Recordings sanitized

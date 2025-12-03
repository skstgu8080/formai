# Code Quality & Standards

> **Python conventions for FormAI**

## General Principles

### Code Style
- Follow PEP 8 style guide
- Use consistent formatting (consider Black or Ruff formatter)
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

### Python
```python
# snake_case for variables and functions
user_name = "John"
def get_user_by_id(user_id: str) -> dict:
    pass

# UPPER_SNAKE_CASE for constants
MAX_RETRY_ATTEMPTS = 3
API_BASE_URL = "https://api.example.com"

# PascalCase for classes
class UserService:
    pass

class ProfileManager:
    pass
```

### Files & Directories
```
# snake_case for Python files
user_service.py
api_routes.py
field_mapper.py

# kebab-case for non-Python files
config-example.json
field-mapping.json
```

### Boolean Variables
```python
# Prefix with is, has, can, should
is_active = True
has_permission = False
can_edit = True
should_refresh = False
```

---

## Function Guidelines

### Single Responsibility
Each function should do one thing well.

```python
# BAD - does too much
def process_profile(profile):
    validate_profile(profile)
    save_to_file(profile)
    send_notification(profile)
    log_activity(profile)

# GOOD - single purpose
def save_profile(profile: dict) -> None:
    """Save profile to JSON file."""
    filepath = get_profile_path(profile["id"])
    save_json(filepath, profile)
```

### Type Hints
Always use type hints for function signatures:
```python
from typing import Optional, List

def get_profile(profile_id: str) -> Optional[dict]:
    """Get profile by ID, returns None if not found."""
    pass

def list_profiles(limit: int = 100) -> List[dict]:
    """List all profiles with optional limit."""
    pass
```

### Docstrings
Use docstrings for public functions:
```python
def normalize_profile(profile: dict) -> dict:
    """
    Normalize profile data to flat structure.

    Converts nested profile formats (e.g., personal.firstName)
    to flat format (firstName) for field mapping.

    Args:
        profile: Profile dict, may be flat or nested

    Returns:
        Flattened profile dict
    """
    pass
```

### Error Handling
```python
# Always handle errors explicitly
async def fetch_profile(profile_id: str) -> dict:
    try:
        filepath = get_profile_path(profile_id)
        return load_json(filepath)
    except FileNotFoundError:
        logger.warning(f"Profile not found: {profile_id}")
        raise ProfileNotFoundError(profile_id)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in profile {profile_id}", exc_info=True)
        raise ProfileCorruptedError(profile_id) from e
```

---

## Code Organization

### Import Order
```python
# 1. Standard library
import os
import json
from pathlib import Path
from typing import Optional, List

# 2. Third-party packages
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# 3. Local modules
from tools.field_mapper import EnhancedFieldMapper
from tools.recording_manager import RecordingManager

# 4. Type imports (if using TYPE_CHECKING)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from selenium.webdriver import Chrome
```

### File Structure
```
formai/
├── formai_server.py       # Main FastAPI app
├── selenium_automation.py # Browser automation
├── tools/
│   ├── __init__.py
│   ├── field_mapper.py
│   ├── recording_manager.py
│   └── utils.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
└── web/
    └── *.html
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
feat: Add profile export functionality

fix: Resolve race condition in automation queue

docs: Update API documentation for recordings endpoint

refactor: Extract validation logic to separate module
```

---

## Code Review Checklist

Before submitting PR:
- [ ] Code follows PEP 8 conventions
- [ ] Functions are small and focused
- [ ] Type hints on all function signatures
- [ ] No commented-out code
- [ ] No print() statements (use logging)
- [ ] Error handling is appropriate
- [ ] Tests are included
- [ ] No secrets or credentials
- [ ] Documentation updated if needed

---

## Performance Guidelines

### Avoid
- Blocking I/O in async functions
- Loading all profiles into memory at once
- Unnecessary file reads in loops
- Memory leaks (clean up browser sessions)

### Optimize
- Use async/await for I/O operations
- Lazy load when appropriate
- Cache expensive computations
- Use generators for large data sets

```python
# GOOD - generator for large file lists
def iter_profiles():
    for filepath in PROFILES_DIR.glob("*.json"):
        yield load_json(filepath)

# BAD - loads all into memory
def get_all_profiles():
    return [load_json(f) for f in PROFILES_DIR.glob("*.json")]
```

---

## Logging

### Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
```

### Usage
```python
logger.debug("Detailed debug info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### What to Log
- Server startup/shutdown
- API requests (method, path, status)
- Automation events (start, complete, error)
- Configuration changes

### What NOT to Log
- Profile data contents
- API keys or secrets
- Passwords or tokens

---

## FastAPI Patterns

### Dependency Injection
```python
from fastapi import Depends

def get_profile_manager():
    return ProfileManager(PROFILES_DIR)

@app.get("/api/profiles")
async def list_profiles(manager: ProfileManager = Depends(get_profile_manager)):
    return manager.list_all()
```

### Response Models
```python
from pydantic import BaseModel

class ProfileResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True

@app.get("/api/profiles/{id}", response_model=ProfileResponse)
async def get_profile(id: str):
    ...
```

### Exception Handling
```python
from fastapi import HTTPException

class ProfileNotFoundError(Exception):
    pass

@app.exception_handler(ProfileNotFoundError)
async def profile_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "PROFILE_NOT_FOUND", "message": str(exc)}}
    )
```

# Data Storage Guidelines

> **FormAI uses JSON file storage - no database required**

## JSON File Storage

FormAI stores all data as JSON files in designated directories. This provides:
- Simple deployment (no database setup)
- Easy backup and restore
- Human-readable data
- Git-friendly (optional version control)

---

## Directory Structure

```
FormAI/
├── profiles/              # User profile data
│   ├── profile-001.json
│   ├── profile-002.json
│   └── ...
├── recordings/            # Chrome DevTools recordings
│   ├── recording-001.json
│   └── ...
├── field_mappings/        # Website-specific field mappings
│   ├── example.com.json
│   └── ...
├── admin_data/            # Admin server data (if enabled)
│   ├── clients.json
│   ├── commands.json
│   └── screenshots/
└── api_keys/              # API key configurations
    └── openrouter.json
```

---

## JSON Schema Conventions

### File Naming
- Use kebab-case for filenames: `profile-001.json`, `field-mapping.json`
- Include ID in filename when applicable
- Use descriptive names for singleton files

### Standard Fields
Every JSON file should include:
```json
{
  "id": "unique-identifier",
  "created_at": "2025-12-01T10:30:00Z",
  "updated_at": "2025-12-01T10:30:00Z"
}
```

### Boolean Fields
Prefix with `is_` or `has_`:
```json
{
  "is_active": true,
  "has_verified": false
}
```

---

## Profile Schema

```json
{
  "id": "profile-001",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-123-4567",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001",
    "country": "USA"
  },
  "personal": {
    "firstName": "John",
    "lastName": "Doe",
    "dateOfBirth": "1990-01-15"
  },
  "business": {
    "company": "Acme Inc",
    "title": "Developer"
  },
  "created_at": "2025-12-01T10:30:00Z",
  "updated_at": "2025-12-01T10:30:00Z"
}
```

### Profile Normalization
FormAI supports both flat and nested profile formats. The server normalizes profiles to a flat structure for field mapping:
```python
# Both of these work:
{"firstName": "John"}                    # Flat
{"personal": {"firstName": "John"}}      # Nested
```

---

## Recording Schema

```json
{
  "id": "recording-001",
  "title": "Example.com Form Fill",
  "url": "https://example.com/form",
  "steps": [
    {
      "type": "navigate",
      "url": "https://example.com/form"
    },
    {
      "type": "click",
      "selectors": ["#submit-button"],
      "offsetX": 10,
      "offsetY": 5
    },
    {
      "type": "change",
      "selectors": ["#email-input"],
      "value": "{{email}}"
    }
  ],
  "created_at": "2025-12-01T10:30:00Z"
}
```

---

## Field Mapping Schema

```json
{
  "id": "example.com",
  "domain": "example.com",
  "mappings": [
    {
      "selector": "#first-name",
      "profile_field": "firstName",
      "type": "text"
    },
    {
      "selector": "#email",
      "profile_field": "email",
      "type": "email"
    }
  ],
  "created_at": "2025-12-01T10:30:00Z"
}
```

---

## File Operations

### Reading JSON Files
```python
import json
from pathlib import Path

def load_json(filepath: Path) -> dict:
    """Load and parse JSON file."""
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
```

### Writing JSON Files
```python
def save_json(filepath: Path, data: dict) -> None:
    """Save data to JSON file with pretty formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

### Atomic Writes
For critical data, use atomic writes to prevent corruption:
```python
import tempfile
import shutil

def atomic_save_json(filepath: Path, data: dict) -> None:
    """Atomically save JSON to prevent corruption."""
    temp_fd, temp_path = tempfile.mkstemp(dir=filepath.parent)
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        shutil.move(temp_path, filepath)
    except:
        os.unlink(temp_path)
        raise
```

---

## Data Validation

### Schema Validation with Pydantic
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

class Profile(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime

def load_profile(filepath: Path) -> Profile:
    data = load_json(filepath)
    return Profile(**data)  # Validates on construction
```

### Required vs Optional Fields
```python
from typing import Optional

class Profile(BaseModel):
    id: str                           # Required
    name: str                         # Required
    email: Optional[str] = None       # Optional
    phone: Optional[str] = None       # Optional
```

---

## Backup & Recovery

### Backup Strategy
```bash
# Backup all data directories
tar -czf formai-backup-$(date +%Y%m%d).tar.gz \
    profiles/ recordings/ field_mappings/ admin_data/
```

### Recovery
```bash
# Restore from backup
tar -xzf formai-backup-20251201.tar.gz
```

### Data Directory Permissions
Ensure proper permissions:
```bash
# Read/write for owner only
chmod 700 profiles/ recordings/
chmod 600 profiles/*.json
```

---

## Environment Separation

| Environment | Data Location |
|-------------|---------------|
| Development | `./profiles/`, `./recordings/` |
| Testing | `./test_data/profiles/`, etc. |
| Production | Same or custom path via config |

For testing, use isolated directories:
```python
# In tests/conftest.py
import tempfile

@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

---

## Data Migration

When schema changes are needed:

1. Create migration script
2. Backup existing data
3. Transform data to new schema
4. Validate transformed data
5. Replace old files

Example migration:
```python
def migrate_profile_v1_to_v2(old_profile: dict) -> dict:
    """Migrate profile from v1 to v2 schema."""
    return {
        **old_profile,
        "schema_version": 2,
        "updated_at": datetime.now().isoformat()
    }
```

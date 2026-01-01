# Sites System

> Manage 292+ sites for batch form automation

## Overview

The Sites System manages URLs for batch auto-fill operations.

**Key File:** `tools/sites_manager.py`

---

## SitesManager Class

**File:** `tools/sites_manager.py:22-201`

```python
from tools.sites_manager import SitesManager

sm = SitesManager()

# List sites
sites = sm.get_all_sites()
enabled = sm.get_enabled_sites()

# CRUD operations
site = sm.add_site("https://example.com/signup", "Example")
sm.update_site(site['id'], {"enabled": False})
sm.delete_site(site['id'])
```

---

## Site Schema

```python
{
    "id": "abc12345",           # 8-char UUID
    "url": "https://...",       # Target URL
    "name": "Example Site",     # Display name
    "enabled": True,            # Include in batch fills
    "created_at": "...",        # ISO timestamp
    "last_run": "...",          # Last fill attempt
    "last_status": "success",   # success/failed/pending
    "fields_filled": 12,        # Fields filled last run
    "fields": [...]             # Analyzed field mappings
}
```

---

## Key Methods

### Site Management

| Method | Purpose |
|--------|---------|
| `get_all_sites()` | List all sites |
| `get_enabled_sites()` | List enabled sites only |
| `get_site(site_id)` | Get single site (partial ID match) |
| `add_site(url, name)` | Add new site |
| `add_sites_bulk(urls)` | Add multiple sites |
| `update_site(id, updates)` | Update site fields |
| `delete_site(id)` | Remove site |
| `toggle_site(id)` | Toggle enabled/disabled |

### Status Tracking

| Method | Purpose |
|--------|---------|
| `update_site_status(id, status, fields)` | Record fill result |
| `get_stats()` | Get aggregate statistics |

### Field Management

| Method | Purpose |
|--------|---------|
| `update_site_fields(id, fields)` | Store analyzed fields |
| `get_site_fields(id)` | Get stored fields |
| `update_field_mapping(id, selector, key)` | Update single mapping |

---

## Database Table

**Table:** `sites`

```sql
CREATE TABLE sites (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    name TEXT,
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    last_status TEXT,
    fields_filled INTEGER DEFAULT 0,
    fields JSON,
    created_at TEXT,
    updated_at TEXT
);
```

---

## Statistics

```python
stats = sm.get_stats()
# Returns:
{
    "total": 292,
    "enabled": 250,
    "success": 180,
    "failed": 30,
    "pending": 40
}
```

---

## Import from Recordings

Import URLs from existing Chrome recordings:

```python
count = sm.import_from_recordings(Path("recordings"))
print(f"Imported {count} sites")
```

---

## Web UI

**Page:** `web/sites.html`

Features:
- List all sites with status
- Add single site or bulk import
- Enable/disable toggle
- Delete sites
- View fill history per site

---

## API Endpoints

### List Sites

```
GET /api/sites
```

Response:
```json
{
  "sites": [...],
  "stats": {
    "total": 292,
    "enabled": 250
  }
}
```

### Add Site

```
POST /api/sites
Content-Type: application/json

{
  "url": "https://example.com/signup",
  "name": "Example Site"
}
```

### Update Site

```
PUT /api/sites/{id}
Content-Type: application/json

{
  "enabled": false,
  "name": "New Name"
}
```

### Delete Site

```
DELETE /api/sites/{id}
```

### Toggle Site

```
POST /api/sites/{id}/toggle
```

---

## CLI Integration

```bash
# List all sites
python cli.py sites

# Fill single site
python cli.py fill <site_id>

# Fill all enabled sites
python cli.py fill-all
```

---

## Profile Integration

Ensure profile has all fields needed by site:

```python
# Get missing fields
missing = sm.get_missing_profile_fields(site_id, profile)

# Add missing fields to profile
sm.ensure_profile_has_fields(profile_id, site_id)
```

---

## Site Files (Legacy)

Sites can also be stored as JSON files in `sites/` directory:

```
sites/
├── example_com.json
├── another_site.json
└── ...
```

Format:
```json
{
  "id": "example_com",
  "url": "https://example.com/signup",
  "name": "Example Site",
  "fields": [...]
}
```

**Note:** SQLite is preferred. JSON files are for backwards compatibility.

---

## Batch Operations

### Add Sites from URL List

```python
urls = [
    "https://site1.com/signup",
    "https://site2.com/register",
    "https://site3.com/join"
]

added = sm.add_sites_bulk(urls)
print(f"Added {len(added)} sites")
```

### Fill All Enabled Sites

```python
from tools.simple_autofill import SimpleAutofill

sites = sm.get_enabled_sites()
engine = SimpleAutofill(headless=True)

for site in sites:
    result = await engine.fill(site['url'], profile)
    sm.update_site_status(
        site['id'],
        "success" if result.success else "failed",
        result.fields_filled
    )
```

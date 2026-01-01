# Update System

> Automatic updates from GitHub releases

## Overview

FormAI checks GitHub for updates and downloads them in the background. Updates are applied on next restart.

**Key File:** `tools/auto_updater.py`

---

## How It Works

```
Server Starts
      ↓
Wait 5 seconds
      ↓
Check GitHub Releases API
      ↓
If newer version found:
      ↓
Download ZIP in background
      ↓
Extract to pending/
      ↓
On next restart:
      ↓
Apply pending update
```

---

## AutoUpdater Class

**File:** `tools/auto_updater.py:24-239`

```python
from tools.auto_updater import updater

# Check for update
if await updater.check_for_update():
    print(f"Update available: {updater.latest_version}")

    # Download
    await updater.download_update()
    print("Update ready - restart to apply")

# Get status
status = updater.get_status()
```

---

## Status Object

```python
{
    "current_version": "1.1.0",
    "latest_version": "1.1.1",
    "update_available": True,
    "update_ready": True,
    "pending_version": "1.1.1",
    "download_progress": 100,
    "error": None
}
```

---

## Key Methods

| Method | Purpose |
|--------|---------|
| `check_for_update()` | Check GitHub for newer version |
| `download_update()` | Download update ZIP |
| `has_pending_update()` | Check if update waiting |
| `get_pending_version()` | Get pending version string |
| `get_status()` | Get full status dict |

---

## GitHub API

Checks `https://api.github.com/repos/{REPO}/releases/latest`

Response parsing:
- `tag_name` → Version (e.g., "v1.1.1")
- `assets` → Download URLs per platform

---

## Platform Detection

| Platform | Asset Name |
|----------|------------|
| Windows x64 | `formai-windows-x64.zip` |
| Windows ARM | `formai-windows-arm64.zip` |
| macOS Intel | `formai-macos-x64.zip` |
| macOS ARM | `formai-macos-arm64.zip` |
| Linux | `formai-linux-x64.zip` |

---

## Version Comparison

Semantic versioning (major.minor.patch):

```python
def _is_newer(latest: str, current: str) -> bool:
    # "1.1.1" > "1.1.0" → True
    # "1.1.0" > "1.1.0" → False
    latest_parts = [int(x) for x in latest.split(".")]
    current_parts = [int(x) for x in current.split(".")]
    return latest_parts > current_parts
```

---

## Update Directory

```
%LOCALAPPDATA%/FormAI/updates/
├── formai-1.1.1.zip     # Downloaded (then deleted)
└── pending/              # Extracted update
    ├── .version         # Version marker
    ├── formai_server.py
    ├── tools/
    └── ...
```

---

## Download Process

1. Create updates directory
2. Stream download ZIP with progress tracking
3. Extract to `pending/` folder
4. Delete ZIP file
5. Write `.version` marker
6. Set `update_ready = True`

---

## Apply Update

**Function:** `apply_pending_update()`

Called at startup before main app runs:

```python
# In formai_entry.py
from tools.auto_updater import apply_pending_update

if apply_pending_update():
    print("Update applied - restarting...")
```

### Steps

1. Check `pending/` exists with `.version`
2. Get current app directory
3. Copy new files over old files
4. Update `version.py`
5. Clean up `pending/` folder

---

## Background Task

**Function:** `check_and_download()`

Runs automatically on server startup:

```python
# In formai_server.py
@app.on_event("startup")
async def startup():
    asyncio.create_task(check_and_download())
```

Waits 5 seconds, then checks and downloads if available.

---

## API Endpoint

```
GET /api/status
```

Response includes update info:
```json
{
  "version": "1.1.0",
  "update_available": true,
  "update_version": "1.1.1",
  "update_ready": true
}
```

---

## WebSocket Notification

When update is ready:
```json
{
  "type": "update_available",
  "version": "1.1.1",
  "ready": true
}
```

---

## Error Handling

```python
try:
    await updater.download_update()
except Exception as e:
    updater.update_error = str(e)
    logger.error(f"Download failed: {e}")
```

Errors stored in `updater.update_error`.

---

## Version Source

**File:** `version.py`

```python
__version__ = "1.1.1"
__author__ = "FormAI Team"
```

Single source of truth for version number.

---

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `GITHUB_REPO` | `"skstgu8080/formai"` | GitHub repository |
| `UPDATE_DIR` | `%LOCALAPPDATA%/FormAI/updates/` | Update storage |

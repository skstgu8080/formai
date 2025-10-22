#!/usr/bin/env python3
"""
FormAI Server - FastAPI with SeleniumBase automation
"""
import os
import sys

# Fix Windows encoding issues
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from colorama import init, Fore, Style

# Initialize colorama for Windows
init()

# Import our automation modules
from selenium_automation import SeleniumAutomation, FormFieldDetector
from tools.gui_automation import GUIHelper, FormFillerGUI

# Import new recording modules
from tools.recording_manager import RecordingManager
from tools.profile_replay_engine import ProfileReplayEngine
from tools.enhanced_field_mapper import EnhancedFieldMapper
from tools.chrome_recorder_parser import ChromeRecorderParser

# Import callback module
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

# Initialize callback system
admin_url = os.getenv("ADMIN_CALLBACK_URL", "")
callback_interval = int(os.getenv("ADMIN_CALLBACK_INTERVAL", "300"))
callback_quiet = os.getenv("ADMIN_CALLBACK_QUIET", "true").lower() == "true"
callback_client = ClientCallback(admin_url=admin_url, interval=callback_interval, quiet=callback_quiet)

# Pydantic models
class Profile(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None

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
    recording_id: str
    profile_id: str
    session_name: Optional[str] = None

class TemplateReplayRequest(BaseModel):
    template_id: str
    profile_id: str
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
                    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Loaded profile: {normalized_name}")
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error loading {file}: {e}")

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
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"FormAI Server v2.0 - SeleniumBase Edition")
    print(f"{'='*50}{Style.RESET_ALL}\n")

    # Load existing profiles
    load_profiles()
    print(f"\n{Fore.GREEN}[OK]{Style.RESET_ALL} Loaded {len(profiles)} profiles")

    # Create necessary directories
    for dir_name in ['profiles', 'field_mappings', 'recordings', 'saved_urls']:
        Path(dir_name).mkdir(exist_ok=True)

    print(f"\n{Fore.YELLOW}>>>{Style.RESET_ALL} Server ready at http://localhost:5511")

    # Start callback system
    callback_client.start()

    yield  # Server runs here

    # Shutdown
    print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")

    # Stop callback system
    await callback_client.stop()

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
    return FileResponse("web/index.html")

@app.get("/profiles")
async def profiles_page():
    """Serve the profiles page"""
    return FileResponse("web/profiles.html")

@app.get("/automation")
async def automation_page():
    """Serve the automation page"""
    return FileResponse("web/automation.html")

@app.get("/recorder")
async def recorder_page():
    """Serve the recorder page"""
    return FileResponse("web/recorder.html")

@app.get("/saved-urls")
async def saved_urls_page():
    """Serve the saved URLs page"""
    return FileResponse("web/saved_urls.html")

@app.get("/saved-pages")
async def saved_pages_page():
    """Serve the saved pages page"""
    return FileResponse("web/saved_pages.html")

@app.get("/settings")
async def settings_page():
    """Serve the settings page"""
    return FileResponse("web/settings.html")

@app.get("/previous-orders")
async def previous_orders_page():
    """Serve the previous orders page"""
    return FileResponse("web/previous_orders.html")

@app.get("/account")
async def account_page():
    """Serve the account page"""
    return FileResponse("web/account.html")

@app.get("/user-data")
async def user_data_page():
    """Serve the user data page"""
    return FileResponse("web/user_data.html")

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
    print(f"{Fore.CYAN}[DEBUG]{Style.RESET_ALL} Received automation request: profile_id={request.profile_id}, url={request.url}, use_stealth={request.use_stealth}")
    print(f"{Fore.CYAN}[DEBUG]{Style.RESET_ALL} Available profiles: {list(profiles.keys())}")

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

    # Create replay engine
    replay_engine = ProfileReplayEngine(use_stealth=True, headless=False)

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
        request.session_name
    )

    return JSONResponse(content={
        "session_id": session_id,
        "message": "Recording replay started",
        "recording_name": recording["recording_name"],
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

    # Create replay engine
    replay_engine = ProfileReplayEngine(use_stealth=True, headless=False)

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
        "template_name": template["template_name"],
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

@app.get("/api/previous-orders")
async def get_previous_orders():
    """Get previous orders/automation history"""
    # Mock data for previous orders
    orders = [
        {
            "id": "ORD-001",
            "status": "completed",
            "target": "Facebook Registration",
            "formsFilled": 1,
            "duration": "2m 34s",
            "date": datetime.now().isoformat(),
            "successRate": 100,
            "profile": "Demo Profile"
        },
        {
            "id": "ORD-002",
            "status": "completed",
            "target": "Macy's Account Creation",
            "formsFilled": 2,
            "duration": "4m 12s",
            "date": datetime.now().isoformat(),
            "successRate": 100,
            "profile": "Demo Profile"
        },
        {
            "id": "ORD-003",
            "status": "failed",
            "target": "Victoria's Secret Registration",
            "formsFilled": 0,
            "duration": "1m 45s",
            "date": datetime.now().isoformat(),
            "successRate": 0,
            "profile": "Demo Profile"
        }
    ]
    return JSONResponse(content=orders)

@app.get("/api/account")
async def get_account():
    """Get account information"""
    account_data = {
        "firstName": "John",
        "lastName": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1 (555) 123-4567",
        "memberSince": "Jan 2024",
        "totalOrders": 24,
        "successRate": 96.2,
        "formsFilled": 1247,
        "settings": {
            "emailNotifications": True,
            "autoSaveProgress": True,
            "darkMode": False
        }
    }
    return JSONResponse(content=account_data)

@app.put("/api/account")
async def update_account(account_data: dict):
    """Update account information"""
    # In a real app, this would save to database
    return JSONResponse(content={"status": "success", "message": "Account updated"})

@app.get("/api/saved-pages")
async def get_saved_pages():
    """Get saved pages"""
    pages = [
        {
            "id": "1",
            "title": "Facebook Registration",
            "url": "https://www.facebook.com/r.php",
            "domain": "facebook.com",
            "formCount": 1,
            "savedAt": datetime.now().isoformat(),
            "status": "completed"
        },
        {
            "id": "2",
            "title": "Macy's Account Creation",
            "url": "https://www.macys.com/account/createaccount",
            "domain": "macys.com",
            "formCount": 2,
            "savedAt": datetime.now().isoformat(),
            "status": "completed"
        }
    ]
    return JSONResponse(content=pages)

@app.get("/api/saved-urls")
async def get_saved_urls():
    """Get saved URLs"""
    urls = [
        {
            "id": "bd045f5f-3ac4-4688-860a-2d07c88054ac",
            "url": "https://www.roboform.com/filling-test-all-fields",
            "name": "RoboForm Test Page",
            "description": "Test page with various form fields",
            "group": "testing",
            "tags": ["forms", "testing"],
            "status": "active",
            "success_rate": None,
            "last_tested": None,
            "test_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]
    return JSONResponse(content=urls)

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
        print(f"WebSocket error: {e}")
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
        except Exception as e:
            print(f"Error stopping session {session_id}: {e}")

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

async def run_recording_replay(session_id: str, recording_id: str, profile: dict, session_name: str = None):
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

        # Run the replay
        results = replay_engine.replay_recording(recording_id, profile, session_name)

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

# Static file serving
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/web", StaticFiles(directory="web"), name="web")

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5511,
        log_level="warning",  # Changed from "info" to suppress WebSocket connection logs
        access_log=False
    )
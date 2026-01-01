# Python Modules Reference

> Complete index of all Python files in FormAI

---

## Root Directory

### Core Servers

| File | Purpose | Port |
|------|---------|------|
| `formai_server.py` | Main FastAPI server | 5511 |
| `admin_server.py` | Admin monitoring server | 5512 |
| `formai_entry.py` | Entry point with auto-update | - |

### Entry Points

| File | Purpose |
|------|---------|
| `cli.py` | Headless CLI commands |
| `version.py` | Version info (`__version__`) |

---

## core/ Directory

| File | Purpose | Doc |
|------|---------|-----|
| `client_callback.py` | Two-way admin communication | [admin-callback.md](admin-callback.md) |
| `worker.py` | Background job worker | - |
| `queue_manager.py` | Job queue management | - |
| `job_models.py` | Pydantic job models | - |

---

## build/ Directory

| File | Purpose |
|------|---------|
| `build_release.py` | Build FormAI.exe |
| `build_site_analyzer.py` | Build SiteAnalyzer.exe |
| `pyinstaller_utils.py` | PyInstaller helpers |
| `build.py` | Build automation |
| `FormAI.spec` | PyInstaller spec file |

---

## tools/ Directory

### AI & Automation Engines

| File | Purpose | Doc |
|------|---------|-----|
| `seleniumbase_agent.py` | Main AI form agent (7-phase pipeline) | [automation-engine.md](automation-engine.md) |
| `simple_autofill.py` | Playwright-based autofill | [automation-engine.md](automation-engine.md) |
| `ollama_agent.py` | Ollama LLM integration | [ai-integration.md](ai-integration.md) |
| `autofill_engine.py` | Core fill logic | [automation-engine.md](automation-engine.md) |

### Field Mapping

| File | Purpose | Doc |
|------|---------|-----|
| `field_analyzer.py` | Analyze form fields | [field-mapping.md](field-mapping.md) |
| `field_mapping_store.py` | SQLite mapping storage | [field-mapping.md](field-mapping.md) |
| `recording_trainer.py` | Learn from Chrome recordings | [recording-system.md](recording-system.md) |

### Sites & Multi-Step

| File | Purpose | Doc |
|------|---------|-----|
| `sites_manager.py` | 292+ sites CRUD | [sites-system.md](sites-system.md) |
| `site_analyzer.py` | Analyze site structure | - |
| `multistep_manager.py` | Wizard form handling | [multistep-forms.md](multistep-forms.md) |

### CAPTCHA & Email

| File | Purpose | Doc |
|------|---------|-----|
| `captcha_solver.py` | 2Captcha integration | [ai-integration.md](ai-integration.md) |
| `email_handler.py` | Email verification flows | - |

### System & Updates

| File | Purpose | Doc |
|------|---------|-----|
| `auto_updater.py` | GitHub release updates | [update-system.md](update-system.md) |
| `update_service.py` | Windows service updater | - |
| `hot_updater.py` | Live code hot-reload | - |
| `system_monitor.py` | System metrics agent | - |
| `agent_memory.py` | AI learning persistence | - |

### Windows Integration

| File | Purpose |
|------|---------|
| `windows_tray.py` | System tray icon |
| `windows_startup.py` | Auto-start on boot |
| `gui_automation.py` | PyAutoGUI helpers |

### Hardware Handlers

| File | Purpose |
|------|---------|
| `camera_handler.py` | Webcam capture |
| `ollama_installer.py` | Auto-install Ollama |

---

## database/ Directory

| File | Purpose | Doc |
|------|---------|-----|
| `__init__.py` | Exports `init_db`, repositories | - |
| `db.py` | SQLite schema & connections | [database.md](database.md) |
| `repositories.py` | Data access classes | [database.md](database.md) |

---

## Key Classes by File

### formai_server.py
```python
app = FastAPI()           # Main app instance
# Endpoints: /api/profiles, /api/sites, /api/automation, /ws
```

### admin_server.py
```python
app = FastAPI()           # Admin app instance
# Endpoints: /api/heartbeat, /api/clients, /api/send_command
```

### client_callback.py
```python
class ClientCallback      # Remote command execution
# Methods: start(), send_heartbeat(), command_handlers
```

### cli.py
```python
# Commands: sites, profiles, fill, fill-all, setup-email
```

### tools/seleniumbase_agent.py
```python
class SeleniumBaseAgent   # AI-powered form filling
# Methods: run(), _phase_detect(), _phase_fill(), _phase_submit()
```

### tools/simple_autofill.py
```python
class SimpleAutofill      # Playwright engine
# Methods: fill(), _fill_field(), _handle_dropdown()
```

### tools/field_mapping_store.py
```python
class FieldMappingStore   # SQLite storage
# Methods: save_mappings(), get_mappings(), has_mappings()
```

### tools/sites_manager.py
```python
class SitesManager        # 292+ sites CRUD
# Methods: get_all_sites(), add_site(), update_site_status()
```

### tools/recording_trainer.py
```python
class RecordingTrainer    # Chrome recording parser
# Methods: extract_mappings(), train_from_recording()
```

### tools/multistep_manager.py
```python
class MultiStepFormManager  # Wizard forms
# Methods: detect_steps(), advance_step(), submit_final()
```

### tools/auto_updater.py
```python
class AutoUpdater         # GitHub updates
# Methods: check_for_update(), download_update()
```

### tools/captcha_solver.py
```python
class CaptchaSolver       # 2Captcha API
# Methods: solve_recaptcha(), solve_hcaptcha()
```

### database/repositories.py
```python
class ProfileRepository   # Profile CRUD
class SiteRepository      # Site CRUD
class MappingRepository   # Field mappings
class HistoryRepository   # Fill history
```

---

## Import Patterns

### Server Imports
```python
from database import init_db, ProfileRepository, SiteRepository
from tools.seleniumbase_agent import SeleniumBaseAgent
from tools.simple_autofill import SimpleAutofill
from client_callback import ClientCallback
```

### CLI Imports
```python
from tools.sites_manager import SitesManager
from tools.simple_autofill import SimpleAutofill
from database import ProfileRepository
```

### Tools Imports
```python
from tools.field_mapping_store import FieldMappingStore
from tools.recording_trainer import RecordingTrainer
from tools.ollama_agent import OllamaAgent
```

---

## File Line Counts

| File | Lines | Complexity |
|------|-------|------------|
| `client_callback.py` | ~1470 | High |
| `tools/seleniumbase_agent.py` | ~800 | High |
| `tools/recording_trainer.py` | ~760 | Medium |
| `formai_server.py` | ~600 | Medium |
| `tools/simple_autofill.py` | ~500 | Medium |
| `tools/multistep_manager.py` | ~450 | Medium |
| `cli.py` | ~430 | Low |
| `admin_server.py` | ~400 | Medium |
| `tools/auto_updater.py` | ~320 | Low |

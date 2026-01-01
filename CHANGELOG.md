# Changelog

All notable changes to FormAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-12-31 (Project Reorganization)

### Added
- **18 Documentation Files** in `.claude/` directory
  - `python-modules.md` - Complete index of all Python files
  - `field-mapping.md` - Pattern dictionary and normalization
  - `automation-engine.md` - 7-phase pipeline documentation
  - `ai-integration.md` - Ollama/2Captcha integration
  - `cli-usage.md` - CLI commands reference
  - `recording-system.md` - Chrome recording import
  - `sites-system.md` - 292+ sites management
  - `multistep-forms.md` - Wizard form handling
  - `update-system.md` - Auto-update mechanism
  - `admin-callback.md` - Remote admin system
- **Project Valuation** (`docs/project-worth.md`) - $150k-$250k development cost analysis

### Changed
- **Project Structure Reorganized**
  - Created `core/` directory for supporting modules (client_callback, worker, queue_manager, job_models)
  - Created `build/` directory for PyInstaller and release scripts
  - Moved batch/shell scripts to `scripts/`
  - Root now has only 5 entry-point Python files
- **Slimmed node_modules** - Removed unused React/Puppeteer packages (67 packages vs 200+)
- **Updated package.json** - Only Tailwind CSS dependencies remain
- **Updated all imports** to use `core.` prefix

### Removed
- `selenium_automation.py` - Legacy, replaced by seleniumbase_agent
- `callback_standalone.py` - Legacy wrapper
- `config/` directory - Unused TypeScript/Tailwind configs
- `project-kit/` - Template files
- `api_keys/` - Migrated to .env
- `training_data/` - 120+ old test screenshots
- `saved_requests/`, `screenshots/`, `downloaded_files/`, `programs/` - Temp data
- `sites/node_modules/` - Stray node_modules (84k lines of junk)

---

## [1.1.1] - 2025-12-31

### Changed
- **Field Mappings migrated to SQLite** - Consistent database storage
  - Created `DomainMappingRepository` for domain-level mappings
  - Added `domain_mappings` table to SQLite schema
  - Migrated 183 JSON files from `field_mappings/` to database
  - Updated all `/api/field-mappings` endpoints to use SQLite
  - Updated `FieldMappingStore` class to use database
  - Deleted legacy `field_mappings/` directory

### Added
- **Mappings Page** (`/mappings`) - Browse and manage learned field mappings
  - View all trained sites with field counts
  - Search by domain
  - View detailed field mappings per site
  - Delete mappings to re-learn sites

### Fixed
- Field mappings API now handles domain/filename mismatches correctly
- Delete mappings works on Windows (file handle issue fixed)

---

## [1.1.0] - 2025-12-29 (Phase 3: Bulk Registration Engine)

### Added
- **10x Parallel Workers** - MAX_PARALLEL_AGENTS increased from 5 to 10
- **Smart Field Matching** - Tiered intelligence (cache -> pattern -> AI)
  - Tier 1: CACHED - Instant lookup from learned_fields.json
  - Tier 2: PATTERN - 50+ common patterns in data/field_patterns.json
  - Tier 3: AI - Only calls Ollama for unknown fields
- **Multi-Step Form Manager** - Handle wizard registration flows
  - Detects step indicators and progress bars
  - Clicks Next for intermediate steps, Submit for final
- **Vision CAPTCHA Solver** - Free auto-solve using Ollama + LLaVA
  - Reads text CAPTCHAs with vision AI
  - Cloudflare/Turnstile bypass via UC Mode
- **Temp Email Handler** - Auto-verify email confirmation flows
  - Creates disposable emails via mail.tm API
  - Polls inbox and extracts verification links/codes

### New Files
- data/field_patterns.json - 50+ form field patterns
- tools/multistep_manager.py - Multi-page form navigation
- tools/captcha_solver.py - Vision CAPTCHA solving
- tools/email_handler.py - Temp email verification

---

## [1.0.13] - 2025-12-29

### Added
- **Real-time System Metrics Dashboard** - Live CPU/memory monitoring on homepage
  - New `/api/system/metrics` endpoint for real-time system stats
  - New `/ws/metrics` WebSocket for 2-second metric pushes
  - System Metrics card with progress bars for CPU/Memory
  - Active agents counter showing parallel capacity
  - Scaling indicator (green=can scale, yellow=at capacity)

- **Error Recovery Agent** - Automatic retry with different strategies
  - 6 recovery strategies: retry_with_delay, scroll_into_view, click_first, human_like_typing, clear_and_refill, alternative_selector
  - Automatically activates when form fill actions fail
  - Tracks attempted strategies per selector to avoid retrying same approach
  - Integrated into CrewCoordinator for seamless error handling

- **Parallel Batch Processing** - Fill multiple sites simultaneously
  - New `fill_sites_parallel()` method using worker pattern
  - Dynamic scaling based on system resources (CPU/memory)
  - Each worker gets its own browser instance
  - Progress tracking per worker with WebSocket updates
  - Batch endpoint now supports `parallel: true` flag
  - Auto-detects optimal number of workers based on hardware

- **Hardware Capability Scan** - System scan at startup
  - Displays CPU cores, speed, memory, network stats
  - Calculates max parallel agents based on resources
  - Performance tier: BEAST MODE (16+ cores), TURBO (8+ cores), STANDARD, ECO
  - Estimated sites/hour calculation

### Changed
- System Monitor Agent now provides real-time metrics to dashboard
- Batch fill endpoint accepts `parallel` and `max_parallel` parameters
- CrewCoordinator reset now includes recovery agent and learner reset

---

## [1.0.12] - 2025-12-28

### Added
- **FormAI.exe Build** - PyInstaller build script for protected executable release
  - `build_release.py` creates standalone 59MB exe
  - Excludes heavy ML libraries (torch, tensorflow, scipy, sklearn, pandas)
  - Source code protected in compiled form
- **Silent Firewall Setup** - Auto-configure Windows Firewall on first run
  - Creates PowerShell script for port 5511 rules
  - Requests UAC elevation once, stores marker file
  - No more "Windows Firewall has blocked..." prompts
- **VPS SSH Management** - Can now edit VPS files directly via paramiko

### Fixed
- **Checkbox/Label Click** - Fix newsletter and consent checkboxes not being clicked
  - Properly detects `<label>` elements and clicks directly (no is_selected check)
  - Added JavaScript click fallback for stubborn elements
  - Added text-based search for labels containing "Subscribe", "newsletter", etc.
- **Playwright Replay** - Added `text/` selector support and offset-based clicks

### Changed
- **Admin Callback** - Removed localhost:5512 from default URLs (production only)
- **Callback Mode** - Set to quiet=True for silent operation

### Removed
- **Statistics Page** - Removed admin_stats.html and sidebar link from admin panel

---

## [1.0.11] - 2025-12-27

### Added
- **Recording URL Input** - Add/edit target URL when importing recordings
  - Auto-fills from navigate step or title
  - Manual override for recordings without URLs
  - Fixes automation failing on recordings with empty URL field

### Fixed
- **Auto-Updater Download** - Fix GitHub download redirects (HTTP 302) not being followed
  - Added `follow_redirects=True` to httpx client
  - Downloads now complete instead of showing stuck "Downloading..." message
- **URL Extraction** - Autofill engine now checks multiple sources for URL:
  - Navigate step URL
  - Recording `url` field
  - Title/recording_name if it looks like a URL
- **Tailwindcss 404** - Removed build directive from CSS that caused browser 404 errors
- **Pydantic Deprecation** - Changed `.dict()` to `.model_dump()` throughout codebase

---

## [1.0.10] - 2025-12-26

### Fixed
- **CAPTCHA Methods** - Use correct SeleniumBase UC Mode methods
  - `uc_gui_handle_cf()` for Cloudflare/Turnstile
  - `uc_gui_handle_rc()` for reCAPTCHA
  - `uc_gui_handle_captcha()` as generic fallback
- **Repository URLs** - Updated all docs to use skstgu8080/formai

---

## [1.0.9] - 2025-12-26

### Added
- **Import Profile Button** - Import JSON profile files directly from the Profiles page
- **Gender Field Fallback** - Autofill engine checks multiple profile field names (sex, gender, genderA)
- **Gender Value Normalization** - Converts m/male to MALE, f/female to FEMALE for dropdown compatibility

### Changed
- **CAPTCHA Solving** - Now uses SeleniumBase built-in methods only (no paid APIs)
- **Release Workflow** - Removed retired macOS-13 Intel build, now builds for:
  - Windows x64
  - macOS Apple Silicon (ARM64)
  - Linux x64

### Removed
- **Paid CAPTCHA APIs** - Removed 2Captcha and Anti-Captcha integration
  - Deleted `tools/captcha_solver.py` (672 lines)
  - Removed CAPTCHA API endpoints from server
  - Removed CAPTCHA service config from Settings page

---

## [1.0.8] - 2025-12-03

### Added
- **Recording Editor UI** - Visual editor to modify selectors and field mappings
  - Edit CSS/XPath selectors for form fields
  - Re-map profile fields to form fields
  - View alternative selectors from original recording
  - Apply suggested mappings with one click
- **Form Validation** - Validate profile data before form submission
  - Email format validation
  - Phone number format validation
  - Password strength checking
  - Required field detection
  - Pre-replay validation with warnings

### Changed
- Added Edit button to recording cards on Recorder page

---

## [Unreleased]

### Added
- **One-Line Installation** - Install FormAI with a single curl/PowerShell command
  - `curl -sSL https://raw.githubusercontent.com/skstgu8080/formai/master/install.sh | bash` (macOS/Linux)
  - `irm https://raw.githubusercontent.com/skstgu8080/formai/master/install.ps1 | iex` (Windows)
- **Cross-Platform Releases** - Pre-built executables for Windows, macOS ARM, Linux
- **GitHub Actions CI/CD** - Automated release builds on version tags

---

## [1.0.0] - 2025-12-01 (Baseline)

### Added
- **Dual-Server Architecture**
  - Client server (port 5511) - Main automation server
  - Admin server (port 5512) - Central monitoring

- **Browser Automation**
  - SeleniumBase with UC (Undetected Chrome) mode
  - CDP (Chrome DevTools Protocol) support
  - Anti-bot detection bypass
  - Human-like interaction delays

- **AI-Powered Form Filling**
  - Smart field detection and mapping
  - Profile-based auto-fill
  - Multiple AI provider support (OpenRouter, Ollama)

- **Recording System**
  - Chrome DevTools recording import
  - Recording replay with profile data
  - Template creation from recordings

- **Profile Management**
  - Create, edit, delete profiles
  - Flat and nested profile format support
  - Profile normalization for field mapping

- **Admin Features**
  - Client heartbeat monitoring
  - Remote command execution
  - Screenshot collection
  - Statistics aggregation

### Technical
- Python 3.x with FastAPI
- SeleniumBase for browser automation
- WebSocket for real-time updates
- JSON file storage (no database required)
- Tailwind CSS for frontend styling

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.10 | 2025-12-26 | Fix CAPTCHA methods, update repo URLs |
| 1.0.9 | 2025-12-26 | Remove paid CAPTCHA APIs, fix gender field, add profile import |
| 1.0.8 | 2025-12-03 | Recording Editor, Form Validation |
| 1.0.0 | 2025-12-01 | Baseline - Python-based FormAI with dual-server architecture |

---

## How to Update This File

1. **Adding a feature**: Add entry under `### Added` in `[Unreleased]`
2. **Fixing a bug**: Add entry under `### Fixed`
3. **Breaking change**: Bump major version, add under `### Changed`
4. **New release**: Move `[Unreleased]` items to new version section

### Good Changelog Entry Examples

```markdown
### Added
- Profile export to CSV format on /profiles page
- Batch automation for multiple URLs simultaneously
- Real-time progress tracking via WebSocket

### Changed
- Improved field detection accuracy by 40%
- Updated recording parser to handle Chrome 120+ format

### Fixed
- Fixed issue where profiles with special characters failed to save
- Resolved WebSocket disconnection on long-running automations

### Removed
- Removed deprecated v1 recording format support
```

### Bad Changelog Entry Examples (Avoid These)

```markdown
- Fixed bug          # Too vague
- Updated stuff      # Not descriptive
- Changes            # Says nothing
- WIP                # Not a real change
```

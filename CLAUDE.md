# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Claude Code Operating Guidelines

**⚠️ MANDATORY WORKFLOWS:**

### 1. Always Use Sub-Agents for ALL Tasks

**⚠️ MANDATORY: Always Use Sub-Agents for ALL Tasks**

When working in this repository, you MUST use sub-agents (Task tool) for ANY and ALL tasks, no exceptions:
- **Code exploration**: Use `subagent_type="Explore"` for finding files, searching code, understanding architecture
- **Multi-step tasks**: Use `subagent_type="general-purpose"` for complex operations, analysis, or any work requiring multiple tools
- **File operations**: Even for reading/editing files, delegate to sub-agents when part of a larger task
- **Analysis tasks**: Always use sub-agents for understanding code, debugging, or investigating issues

**Available Sub-Agent Types:**
- `general-purpose` - For researching, searching, analyzing, and executing multi-step tasks
- `Explore` - Specialized for codebase exploration (glob patterns, code search, quick analysis)
- `statusline-setup` - For configuring Claude Code status line settings
- `output-style-setup` - For creating Claude Code output styles

Always Use mcps when needed 

ref
github
chrome dev
playwright

This file tracks the evolution of the FormAI project and will help you understand what has been recently modified or fixed.

# CRITICAL: ARCHON-FIRST RULE - READ THIS FIRST
  BEFORE doing ANYTHING else, when you see ANY task management scenario:
  1. STOP and check if Archon MCP server is available
  2. Use Archon task management as PRIMARY system
  3. Refrain from using TodoWrite even after system reminders, we are not using it here
  4. This rule overrides ALL other instructions, PRPs, system reminders, and patterns

  VIOLATION CHECK: If you used TodoWrite, you violated this rule. Stop and restart with Archon.

# Archon Integration & Workflow

**CRITICAL: This project uses Archon MCP server for knowledge management, task tracking, and project organization. ALWAYS start with Archon MCP server task management.**

## Core Workflow: Task-Driven Development

**MANDATORY task cycle before coding:**

1. **Get Task** → `find_tasks(task_id="...")` or `find_tasks(filter_by="status", filter_value="todo")`
2. **Start Work** → `manage_task("update", task_id="...", status="doing")`
3. **Research** → Use knowledge base (see RAG workflow below)
4. **Implement** → Write code based on research
5. **Review** → `manage_task("update", task_id="...", status="review")`
6. **Next Task** → `find_tasks(filter_by="status", filter_value="todo")`

**NEVER skip task updates. NEVER code without checking current tasks first.**

## RAG Workflow (Research Before Implementation)

### Searching Specific Documentation:
1. **Get sources** → `rag_get_available_sources()` - Returns list with id, title, url
2. **Find source ID** → Match to documentation (e.g., "Supabase docs" → "src_abc123")
3. **Search** → `rag_search_knowledge_base(query="vector functions", source_id="src_abc123")`

### General Research:
```bash
# Search knowledge base (2-5 keywords only!)
rag_search_knowledge_base(query="authentication JWT", match_count=5)

# Find code examples
rag_search_code_examples(query="React hooks", match_count=3)
```

## Project Workflows

### New Project:
```bash
# 1. Create project
manage_project("create", title="My Feature", description="...")

# 2. Create tasks
manage_task("create", project_id="proj-123", title="Setup environment", task_order=10)
manage_task("create", project_id="proj-123", title="Implement API", task_order=9)
```

### Existing Project:
```bash
# 1. Find project
find_projects(query="auth")  # or find_projects() to list all

# 2. Get project tasks
find_tasks(filter_by="project", filter_value="proj-123")

# 3. Continue work or create new tasks
```

## Tool Reference

**Projects:**
- `find_projects(query="...")` - Search projects
- `find_projects(project_id="...")` - Get specific project
- `manage_project("create"/"update"/"delete", ...)` - Manage projects

**Tasks:**
- `find_tasks(query="...")` - Search tasks by keyword
- `find_tasks(task_id="...")` - Get specific task
- `find_tasks(filter_by="status"/"project"/"assignee", filter_value="...")` - Filter tasks
- `manage_task("create"/"update"/"delete", ...)` - Manage tasks

**Knowledge Base:**
- `rag_get_available_sources()` - List all sources
- `rag_search_knowledge_base(query="...", source_id="...")` - Search docs
- `rag_search_code_examples(query="...", source_id="...")` - Find code

## Important Notes

- Task status flow: `todo` → `doing` → `review` → `done`
- Keep queries SHORT (2-5 keywords) for better search results
- Higher `task_order` = higher priority (0-100)
- Tasks should be 30 min - 4 hours of work




## Architecture Overview

FormAI is a **Python-based browser automation platform** with a dual-server architecture:

### Dual-Server Architecture

**Client Server** (`formai_server.py` - Port 5511)
- Main automation server for end users
- FastAPI framework with WebSocket support
- SeleniumBase browser automation engine
- AI-powered form field mapping
- Real-time progress updates via WebSocket
- Anti-bot detection bypass with UC mode
- Profile-based form filling
- Recording import and replay

**Admin Server** (`admin_server.py` - Port 5512)
- Central monitoring server for managing multiple installations
- Receives heartbeats from client installations
- Remote command execution via callback system
- Installation health monitoring
- Screenshot collection from clients
- Statistics aggregation across all installations

**Admin Callback System** (`client_callback.py`)
- Two-way communication between client and admin servers
- Heartbeat reporting (configurable interval, default 5 minutes)
- Remote command execution handlers
- System information collection
- Optional - only enabled when ADMIN_URL is configured

### Technology Stack

**Backend:**
- Python 3.x with FastAPI
- SeleniumBase for browser automation
- PyAutoGUI for CAPTCHA assistance
- Uvicorn ASGI server
- WebSockets for real-time communication

**Frontend:**
- HTML/CSS/JavaScript (no framework)
- Tailwind CSS for styling
- Modular JavaScript in static/js/
- WebSocket client for live updates

**Browser Automation:**
- SeleniumBase with UC (Undetected Chrome) mode
- CDP (Chrome DevTools Protocol) support
- Anti-bot detection bypass
- Human-like interaction delays

## UI/Styling Guidelines

**⚠️ CRITICAL: Theme-Aware Button Styling**

When creating new UI components, buttons, or interactive elements, ALWAYS follow these styling rules for proper light/dark mode support:

### Action Buttons (Primary Interactive Elements)
**USE:** `bg-secondary hover:bg-secondary/90 text-secondary-foreground`
- ✅ Correct: Colored buttons in both light and dark modes
- ❌ NEVER use: `bg-primary` for action buttons (creates white buttons in dark mode)

**Examples:**
```html
<!-- ✅ CORRECT: Action buttons -->
<button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md">
    Start Camera
</button>
<button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md">
    Scan Devices
</button>

<!-- ❌ WRONG: Will appear white in dark mode -->
<button class="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md">
    Action Button
</button>
```

### Destructive Actions (Delete, Stop, Cancel)
**USE:** `bg-destructive hover:bg-destructive/90 text-destructive-foreground`

```html
<!-- ✅ CORRECT: Destructive actions -->
<button class="bg-destructive hover:bg-destructive/90 text-destructive-foreground px-4 py-2 rounded-md">
    Delete
</button>
<button class="bg-destructive hover:bg-destructive/90 text-destructive-foreground px-4 py-2 rounded-md">
    Stop Camera
</button>
```

### Neutral/Cancel Buttons (Secondary Actions)
**USE:** `bg-secondary hover:bg-secondary/90 text-secondary-foreground`

```html
<!-- ✅ CORRECT: Secondary/cancel actions -->
<button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md">
    Cancel
</button>
<button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md">
    Close
</button>
```

### Status Badges (Fixed Semantic Colors)
**OK to use:** Fixed colors like `bg-green-500`, `bg-red-500`, `bg-yellow-500` with `text-white`
- These are semantic indicators and should NOT change with theme

```html
<!-- ✅ CORRECT: Status indicators with fixed colors -->
<span class="bg-green-500 text-white px-3 py-1 rounded-full">Online</span>
<span class="bg-red-500 text-white px-3 py-1 rounded-full">Offline</span>
```

### Dynamic Button States
When buttons have multiple states (active/inactive), use conditional classes:

```html
<!-- ✅ CORRECT: Conditional styling with proper theme awareness -->
<button class="${isActive ? 'bg-green-500 hover:bg-green-600 text-white' : 'bg-secondary hover:bg-secondary/90 text-secondary-foreground'}">
    ${isActive ? 'Active' : 'Start'}
</button>
```

### Theme Color Reference
- **Light Mode:**
  - `bg-primary` = Dark (#18181b)
  - `bg-secondary` = Light gray (#f4f4f5)
  - `bg-destructive` = Red

- **Dark Mode:**
  - `bg-primary` = Light (#fafafa) ⚠️ Creates white buttons!
  - `bg-secondary` = Dark gray (#262626) ✅ Proper colored buttons
  - `bg-destructive` = Red

**Key Takeaway:** `bg-primary` inverts between light/dark, making it unsuitable for action buttons. Always use `bg-secondary` for consistent colored buttons across themes.

## Essential Commands

### Development Servers

**Start Client Server (Port 5511):**
```bash
python formai_server.py
# or
start-python.bat  # Windows with auto-setup
```

**Start Admin Server (Port 5512):**
```bash
python admin_server.py
# or
start-admin.bat  # Windows
```

### CSS Development
```bash
npm run build-css   # Build Tailwind CSS once
npm run watch-css   # Watch and rebuild CSS automatically
```

### Browser Setup
```bash
scripts/install-browser.bat  # Install SeleniumBase browsers
```

### Testing
```bash
python tests/test_server.py           # Test basic server
python tests/test_roboform.py         # Test RoboForm integration
python tests/test_roboform_simple.py  # Simple automation test
```

## Project Structure

```
formai-admin/
├── formai_server.py          # Client server (port 5511) - 1034 lines
├── admin_server.py           # Admin server (port 5512) - 443 lines
├── client_callback.py        # Admin callback system - 784 lines
├── selenium_automation.py    # Core automation engine - 755 lines
│
├── web/                      # HTML pages
│   ├── index.html           # Main dashboard
│   ├── profiles.html        # Profile management
│   ├── automation.html      # Automation interface
│   ├── recorder.html        # Recording management
│   ├── settings.html        # Settings page
│   ├── admin.html           # Admin monitoring dashboard
│   └── [other pages]
│
├── static/                   # Static assets
│   ├── css/                 # Stylesheets
│   │   ├── input.css        # Tailwind input
│   │   └── tailwind.css     # Built output
│   ├── js/                  # JavaScript modules
│   └── Models.json          # AI model configurations
│
├── tools/                    # Automation utilities
│   ├── enhanced_field_mapper.py      # Smart field detection
│   ├── chrome_recorder_parser.py     # Parse Chrome recordings
│   ├── profile_replay_engine.py      # Profile-based replay
│   ├── recording_manager.py          # Recording management
│   ├── gui_automation.py             # PyAutoGUI helpers
│   └── training_logger.py            # AI training data
│
├── profiles/                 # User profile JSON files
├── field_mappings/          # Form field mappings
├── recordings/              # Browser recordings
├── admin_data/              # Admin server data
│   ├── clients.json         # Client installations
│   ├── commands.json        # Pending commands
│   └── screenshots/         # Client screenshots
│
├── scripts/                 # Utility scripts
├── docs/                    # Documentation
├── tests/                   # Test files
├── config/                  # Configuration files
└── requirements.txt         # Python dependencies
```

## Key Python Modules

### Core Servers
- `formai_server.py` - Main client server with FastAPI routing, WebSocket handling, automation orchestration
- `admin_server.py` - Admin monitoring server for managing multiple installations
- `client_callback.py` - Client-to-admin callback system with heartbeat and command execution

### Automation Engine
- `selenium_automation.py` - SeleniumBase automation with UC mode, CDP support, form detection
  - Class: `SeleniumAutomation` - Main automation class
  - Class: `FormFieldDetector` - Field detection and mapping

### Tools & Utilities
- `tools/enhanced_field_mapper.py` - `EnhancedFieldMapper` - AI-powered field matching
- `tools/chrome_recorder_parser.py` - `ChromeRecorderParser` - Parse Chrome DevTools recordings
- `tools/profile_replay_engine.py` - `ProfileReplayEngine` - Replay recordings with profile data
- `tools/recording_manager.py` - `RecordingManager` - Recording import/export/management
- `tools/gui_automation.py` - PyAutoGUI helper classes for manual interventions
- `tools/enhanced_field_detector.py` - Advanced field detection algorithms
- `tools/training_logger.py` - AI training data collection and logging

## API Endpoints

### Client Server (Port 5511)

**Profile Management:**
- `GET /api/profiles` - List all profiles
- `GET /api/profiles/{id}` - Get specific profile
- `POST /api/profiles` - Create new profile
- `PUT /api/profiles/{id}` - Update profile
- `DELETE /api/profiles/{id}` - Delete profile

**Automation:**
- `POST /api/automation/start` - Start automation job
- `POST /api/automation/stop` - Stop all automation
- `POST /api/automation/stop/{session_id}` - Stop specific session
- `GET /api/status` - Get server status
- `WS /ws` - WebSocket for real-time updates

**Field Mappings:**
- `GET /api/field-mappings` - Get all field mappings
- `POST /api/field-mappings` - Create field mapping

**Recordings:**
- `POST /api/recordings/import-chrome` - Import Chrome DevTools recording
- `GET /api/recordings` - List all recordings
- `GET /api/recordings/{id}` - Get specific recording
- `DELETE /api/recordings/{id}` - Delete recording
- `POST /api/recordings/{id}/replay` - Replay recording with profile
- `GET /api/recordings/stats` - Get recording statistics
- `POST /api/recordings/{id}/create-template` - Create template from recording
- `GET /api/recordings/{id}/analyze` - Analyze recording fields

**Data Management:**
- `GET /api/api-keys` - Get API keys configuration

### Admin Server (Port 5512)

**Client Monitoring:**
- `POST /api/heartbeat` - Receive client heartbeat (called by client_callback.py)
- `GET /api/clients` - List all registered clients
- `GET /api/stats` - Get aggregated statistics

**Remote Commands:**
- `POST /api/send_command` - Send command to client(s)
- `POST /api/command_result` - Receive command result from client
- `GET /api/command_results` - Get all command results
- `GET /api/command_results/{id}` - Get specific command result

**Screenshots:**
- `GET /api/screenshots` - List all screenshots
- `GET /api/screenshots/{filename}` - Get specific screenshot

**Dashboard:**
- `GET /` - Admin dashboard UI (web/admin.html)

## Admin Callback System

The admin callback system enables centralized monitoring and control:

### Client-Side Setup
1. Set `ADMIN_URL` in `.env` file (e.g., `ADMIN_URL=http://admin.example.com:5512`)
2. Client automatically initializes callback on startup
3. Sends heartbeats every 5 minutes (configurable)
4. Polls for commands from admin server

### Heartbeat Data
Each heartbeat includes:
- Client ID (generated on first run)
- Hostname and IP address
- Operating system and Python version
- Server status (uptime, active sessions)
- System resources (CPU, memory, disk)
- Profile count
- Timestamp

### Remote Commands
Admin can send commands to clients:
- `ping` - Test connectivity
- `get_status` - Get detailed status
- `restart` - Restart server
- `update_config` - Update configuration
- Custom commands via registered handlers

### Command Execution Flow
1. Admin sends command via `POST /api/send_command`
2. Client polls and receives command
3. Client executes command via registered handler
4. Client sends result back via `POST /api/command_result`
5. Admin retrieves result via `GET /api/command_results/{id}`

## Data Storage

All data stored as JSON files (no database required):

- **Profiles** (`profiles/*.json`) - User profile data with personal/business information
- **Field Mappings** (`field_mappings/*.json`) - Website-specific field mappings
- **Recordings** (`recordings/*.json`) - Imported Chrome DevTools recordings
- **Admin Data** (`admin_data/`) - Client registry, commands, screenshots

## Development Workflow

### Starting Development
1. Install dependencies: `pip install -r requirements.txt`
2. Install Node dependencies: `npm install`
3. Build CSS: `npm run build-css`
4. Start client server: `python formai_server.py`
5. (Optional) Start admin server: `python admin_server.py`

### Making Changes

**Backend Changes:**
- Edit Python files directly
- Restart server to apply changes
- Check logs for errors

**Frontend Changes:**
- Edit HTML files in `web/`
- Edit JavaScript in `static/js/`
- For CSS: Edit `static/css/input.css`, run `npm run build-css`
- Refresh browser to see changes

**Testing Changes:**
- Access client at http://localhost:5511
- Access admin at http://localhost:5512
- Use browser DevTools for debugging
- Check server console for errors

### Common Development Tasks

**Add New API Endpoint:**
1. Add endpoint function to `formai_server.py` or `admin_server.py`
2. Use `@app.get()` or `@app.post()` decorator
3. Define Pydantic model if needed
4. Test with curl or frontend

**Add New Page:**
1. Create HTML file in `web/`
2. Add route in server: `@app.get("/page-name")`
3. Return `FileResponse("web/page-name.html")`
4. Add navigation link in sidebar

**Add Profile Field:**
1. Update profile JSON structure in `profiles/`
2. Update normalization logic in `formai_server.py`
3. Update frontend form in `web/profiles.html`
4. Update field mapper if needed

**Add Remote Command:**
1. Register handler in `client_callback.py`: `self.register_handler("command_name", handler_function)`
2. Admin sends command via API
3. Client executes and returns result

## Important Notes

- **No Rust** - This is a pure Python project (despite outdated README references)
- **Port 5511** - Client server (main automation)
- **Port 5512** - Admin server (monitoring)
- **WebSocket** - Used for real-time automation updates on client server
- **UC Mode** - Undetected Chrome mode bypasses most bot detection
- **CDP Mode** - Chrome DevTools Protocol for enhanced control
- **Profile Normalization** - Handles multiple profile JSON formats (flat/nested structures)
- **Admin Callback** - Optional, requires ADMIN_URL environment variable
- **SeleniumBase** - Handles browser driver management automatically
- **No Database** - All data stored as JSON files

## Configuration Files

- `requirements.txt` - Python dependencies (FastAPI, SeleniumBase, PyAutoGUI, etc.)
- `package.json` - Node.js scripts for Tailwind CSS
- `.env` - Environment variables (API keys, ADMIN_URL)
- `.env.example` - Example environment configuration
- `static/Models.json` - AI model configurations for field mapping

## Browser Automation Features

- **UC Mode** - Undetected Chrome bypasses bot detection
- **CDP Mode** - Chrome DevTools Protocol for stealth
- **Smart Field Detection** - AI-powered form field identification
- **Profile Auto-fill** - Automatic form filling from profiles
- **Recording Replay** - Import and replay Chrome recordings
- **CAPTCHA Assistance** - PyAutoGUI for manual solving
- **Human-like Delays** - Realistic interaction timing
- **Screenshot Capture** - Automatic screenshots during automation
- **Error Recovery** - Retry logic and fallback strategies

## Quick Start

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Build CSS**: `npm install && npm run build-css`
3. **Start client server**: `python formai_server.py` (opens http://localhost:5511)
4. **Start admin server** (optional): `python admin_server.py` (opens http://localhost:5512)
5. **Create profile**: Use the Profiles page to add your first profile
6. **Import recordings**: Use the Recorder page to import Chrome DevTools recordings
7. **Run automation**: Use recordings or automation page to fill forms

## Admin Server Setup (Optional)

To enable centralized monitoring:

1. **On admin machine**:
   - Run `python admin_server.py` or `start-admin.bat`
   - Server starts on port 5512
   - Access dashboard at http://localhost:5512

2. **On client machines**:
   - Create `.env` file with: `ADMIN_URL=http://admin-server-ip:5512`
   - Start client normally
   - Client automatically reports to admin server

3. **Monitor clients**:
   - View all clients on admin dashboard
   - See real-time status and statistics
   - Send commands remotely
   - View client screenshots

   # CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Beta Development Guidelines

**Local-only deployment** - each user runs their own instance.

### Core Principles

- **No backwards compatibility; we follow a fix‑forward approach** — remove deprecated code immediately
- **Detailed errors over graceful failures** - we want to identify and fix issues fast
- **Break things to improve them** - beta is for rapid iteration
- **Continuous improvement** - embrace change and learn from mistakes
- **KISS** - keep it simple
- **DRY** when appropriate
- **YAGNI** — don't implement features that are not needed

### Error Handling

**Core Principle**: In beta, we need to intelligently decide when to fail hard and fast to quickly address issues, and when to allow processes to complete in critical services despite failures. Read below carefully and make intelligent decisions on a case-by-case basis.

#### When to Fail Fast and Loud (Let it Crash!)

These errors should stop execution and bubble up immediately: (except for crawling flows)

- **Service startup failures** - If credentials, database, or any service can't initialize, the system should crash with a clear error
- **Missing configuration** - Missing environment variables or invalid settings should stop the system
- **Database connection failures** - Don't hide connection issues, expose them
- **Authentication/authorization failures** - Security errors must be visible and halt the operation
- **Data corruption or validation errors** - Never silently accept bad data, Pydantic should raise
- **Critical dependencies unavailable** - If a required service is down, fail immediately
- **Invalid data that would corrupt state** - Never store zero embeddings, null foreign keys, or malformed JSON

#### When to Complete but Log Detailed Errors

These operations should continue but track and report failures clearly:

- **Batch processing** - When crawling websites or processing documents, complete what you can and report detailed failures for each item
- **Background tasks** - Embedding generation, async jobs should finish the queue but log failures
- **WebSocket events** - Don't crash on a single event failure, log it and continue serving other clients
- **Optional features** - If projects/tasks are disabled, log and skip rather than crash
- **External API calls** - Retry with exponential backoff, then fail with a clear message about what service failed and why

#### Critical Nuance: Never Accept Corrupted Data

When a process should continue despite failures, it must **skip the failed item entirely** rather than storing corrupted data

#### Error Message Guidelines

- Include context about what was being attempted when the error occurred
- Preserve full stack traces with `exc_info=True` in Python logging
- Use specific exception types, not generic Exception catching
- Include relevant IDs, URLs, or data that helps debug the issue
- Never return None/null to indicate failure - raise an exception with details
- For batch operations, always report both success count and detailed failure list

### Code Quality

- Remove dead code immediately rather than maintaining it - no backward compatibility or legacy functions
- Avoid backward compatibility mappings or legacy function wrappers
- Fix forward
- Focus on user experience and feature completeness
- When updating code, don't reference what is changing (avoid keywords like SIMPLIFIED, ENHANCED, LEGACY, CHANGED, REMOVED), instead focus on comments that document just the functionality of the code
- When commenting on code in the codebase, only comment on the functionality and reasoning behind the code. Refrain from speaking to Archon being in "beta" or referencing anything else that comes from these global rules.

## Development Commands

### Frontend (archon-ui-main/)

```bash
npm run dev              # Start development server on port 3737
npm run build            # Build for production
npm run lint             # Run ESLint on legacy code (excludes /features)
npm run lint:files path/to/file.tsx  # Lint specific files

# Biome for /src/features directory only
npm run biome            # Check features directory
npm run biome:fix        # Auto-fix issues
npm run biome:format     # Format code (120 char lines)
npm run biome:ai         # Machine-readable JSON output for AI
npm run biome:ai-fix     # Auto-fix with JSON output

# Testing
npm run test             # Run all tests in watch mode
npm run test:ui          # Run with Vitest UI interface
npm run test:coverage:stream  # Run once with streaming output
vitest run src/features/projects  # Test specific directory

# TypeScript
npx tsc --noEmit         # Check all TypeScript errors
npx tsc --noEmit 2>&1 | grep "src/features"  # Check features only
```

### Backend (python/)

```bash
# Using uv package manager (preferred)
uv sync --group all      # Install all dependencies
uv run python -m src.server.main  # Run server locally on 8181
uv run pytest            # Run all tests
uv run pytest tests/test_api_essentials.py -v  # Run specific test
uv run ruff check        # Run linter
uv run ruff check --fix  # Auto-fix linting issues
uv run mypy src/         # Type check

# Docker operations
docker compose up --build -d       # Start all services
docker compose --profile backend up -d  # Backend only (for hybrid dev)
docker compose logs -f archon-server   # View server logs
docker compose logs -f archon-mcp      # View MCP server logs
docker compose restart archon-server   # Restart after code changes
docker compose down      # Stop all services
docker compose down -v   # Stop and remove volumes
```

### Quick Workflows

```bash
# Hybrid development (recommended) - backend in Docker, frontend local
make dev                 # Or manually: docker compose --profile backend up -d && cd archon-ui-main && npm run dev

# Full Docker mode
make dev-docker          # Or: docker compose up --build -d

# Run linters before committing
make lint                # Runs both frontend and backend linters
make lint-fe             # Frontend only (ESLint + Biome)
make lint-be             # Backend only (Ruff + MyPy)

# Testing
make test                # Run all tests
make test-fe             # Frontend tests only
make test-be             # Backend tests only
```

## Architecture Overview

@PRPs/ai_docs/ARCHITECTURE.md

#### TanStack Query Implementation

For architecture and file references:
@PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md

For code patterns and examples:
@PRPs/ai_docs/QUERY_PATTERNS.md

#### Service Layer Pattern

See implementation examples:
- API routes: `python/src/server/api_routes/projects_api.py`
- Service layer: `python/src/server/services/project_service.py`
- Pattern: API Route → Service → Database

#### Error Handling Patterns

See implementation examples:
- Custom exceptions: `python/src/server/exceptions.py`
- Exception handlers: `python/src/server/main.py` (search for @app.exception_handler)
- Service error handling: `python/src/server/services/` (various services)

## ETag Implementation

@PRPs/ai_docs/ETAG_IMPLEMENTATION.md

## Database Schema

Key tables in Supabase:

- `sources` - Crawled websites and uploaded documents
  - Stores metadata, crawl status, and configuration
- `documents` - Processed document chunks with embeddings
  - Text chunks with vector embeddings for semantic search
- `projects` - Project management (optional feature)
  - Contains features array, documents, and metadata
- `tasks` - Task tracking linked to projects
  - Status: todo, doing, review, done
  - Assignee: User, Archon, AI IDE Agent
- `code_examples` - Extracted code snippets
  - Language, summary, and relevance metadata

## API Naming Conventions

@PRPs/ai_docs/API_NAMING_CONVENTIONS.md

Use database values directly (no FE mapping; type‑safe end‑to‑end from BE upward):

## Environment Variables

Required in `.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co  # Or http://host.docker.internal:8000 for local
SUPABASE_SERVICE_KEY=your-service-key-here      # Use legacy key format for cloud Supabase
```

Optional variables and full configuration:
See `python/.env.example` for complete list

### Repository Configuration

Repository information (owner, name) is centralized in `python/src/server/config/version.py`:
- `GITHUB_REPO_OWNER` - GitHub repository owner (default: "coleam00")
- `GITHUB_REPO_NAME` - GitHub repository name (default: "Archon")

This is the single source of truth for repository configuration. All services (version checking, bug reports, etc.) should import these constants rather than hardcoding repository URLs.

Environment variable override: `GITHUB_REPO="owner/repo"` can be set to override defaults.

## Common Development Tasks

### Add a new API endpoint

1. Create route handler in `python/src/server/api_routes/`
2. Add service logic in `python/src/server/services/`
3. Include router in `python/src/server/main.py`
4. Update frontend service in `archon-ui-main/src/features/[feature]/services/`

### Add a new UI component in features directory

**IMPORTANT**: Review UI design standards in `@PRPs/ai_docs/UI_STANDARDS.md` before creating UI components.

1. Use Radix UI primitives from `src/features/ui/primitives/`
2. Create component in relevant feature folder under `src/features/[feature]/components/`
3. Define types in `src/features/[feature]/types/`
4. Use TanStack Query hook from `src/features/[feature]/hooks/`
5. Apply Tron-inspired glassmorphism styling with Tailwind
6. Follow responsive design patterns (mobile-first with breakpoints)
7. Ensure no dynamic Tailwind class construction (see UI_STANDARDS.md Section 2)

### Add or modify MCP tools

1. MCP tools are in `python/src/mcp_server/features/[feature]/[feature]_tools.py`
2. Follow the pattern:
   - `find_[resource]` - Handles list, search, and get single item operations
   - `manage_[resource]` - Handles create, update, delete with an "action" parameter
3. Register tools in the feature's `__init__.py` file

### Debug MCP connection issues

1. Check MCP health: `curl http://localhost:8051/health`
2. View MCP logs: `docker compose logs archon-mcp`
3. Test tool execution via UI MCP page
4. Verify Supabase connection and credentials

### Fix TypeScript/Linting Issues

```bash
# TypeScript errors in features
npx tsc --noEmit 2>&1 | grep "src/features"

# Biome auto-fix for features
npm run biome:fix

# ESLint for legacy code
npm run lint:files src/components/SomeComponent.tsx
```

## Code Quality Standards

### Frontend

- **TypeScript**: Strict mode enabled, no implicit any
- **Biome** for `/src/features/`: 120 char lines, double quotes, trailing commas
- **ESLint** for legacy code: Standard React rules
- **Testing**: Vitest with React Testing Library

### Backend

- **Python 3.12** with 120 character line length
- **Ruff** for linting - checks for errors, warnings, unused imports
- **Mypy** for type checking - ensures type safety
- **Pytest** for testing with async support

## MCP Tools Available

When connected to Claude/Cursor/Windsurf, the following tools are available:

### Knowledge Base Tools

- `archon:rag_search_knowledge_base` - Search knowledge base for relevant content
- `archon:rag_search_code_examples` - Find code snippets in the knowledge base
- `archon:rag_get_available_sources` - List available knowledge sources
- `archon:rag_list_pages_for_source` - List all pages for a given source (browse documentation structure)
- `archon:rag_read_full_page` - Retrieve full page content by page_id or URL

### Project Management

- `archon:find_projects` - Find all projects, search, or get specific project (by project_id)
- `archon:manage_project` - Manage projects with actions: "create", "update", "delete"

### Task Management

- `archon:find_tasks` - Find tasks with search, filters, or get specific task (by task_id)
- `archon:manage_task` - Manage tasks with actions: "create", "update", "delete"

### Document Management

- `archon:find_documents` - Find documents, search, or get specific document (by document_id)
- `archon:manage_document` - Manage documents with actions: "create", "update", "delete"

### Version Control

- `archon:find_versions` - Find version history or get specific version
- `archon:manage_version` - Manage versions with actions: "create", "restore"

## Important Notes

- Projects feature is optional - toggle in Settings UI
- TanStack Query handles all data fetching; smart HTTP polling is used where appropriate (no WebSockets)
- Frontend uses Vite proxy for API calls in development
- Python backend uses `uv` for dependency management
- Docker Compose handles service orchestration
- TanStack Query for all data fetching - NO PROP DRILLING
- Vertical slice architecture in `/features` - features own their sub-features

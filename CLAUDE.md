# FormAI

## Overview
- **Type**: Python Browser Automation Platform
- **Stack**: Python 3.x, FastAPI, SeleniumBase, Tailwind CSS
- **Architecture**: Dual-server (Client 5511 + Admin 5512)
- **Repository**: Local deployment

This CLAUDE.md is the authoritative source for FormAI development guidelines.

---

## Universal Rules

### MUST
- **MUST** explore codebase before making changes
- **MUST** run tests before committing
- **MUST** update CHANGELOG.md after significant changes
- **MUST** use Pydantic for request validation
- **MUST** follow existing code patterns and conventions
- **MUST** use sub-agents for complex tasks

### SHOULD
- **SHOULD** use the documentation checklist after features
- **SHOULD** write tests for new functionality
- **SHOULD** keep functions small and focused
- **SHOULD** use type hints on all functions

### MUST NOT
- **MUST NOT** commit secrets, API keys, or tokens
- **MUST NOT** hardcode file paths
- **MUST NOT** expose stack traces to API responses
- **MUST NOT** bypass input validation

---

## Claude Code Operating Guidelines

### Always Use Sub-Agents for ALL Tasks

When working in this repository, use sub-agents (Task tool) for tasks:
- **Code exploration**: Use `subagent_type="Explore"` for finding files, searching code
- **Multi-step tasks**: Use `subagent_type="general-purpose"` for complex operations
- **Analysis tasks**: Use sub-agents for understanding code, debugging

**Available Sub-Agent Types:**
- `general-purpose` - For researching, searching, analyzing, multi-step tasks
- `Explore` - Specialized for codebase exploration
- `Plan` - For planning complex implementations

### MCP Servers Available
- ref - Documentation search
- github - Repository operations
- chrome-devtools - Browser debugging
- playwright - Browser automation

---

## Archon Integration & Workflow

**This project uses Archon MCP server for task management when available.**

### Task-Driven Development

**Task cycle before coding:**

1. **Get Task** → `find_tasks(task_id="...")` or `find_tasks(filter_by="status", filter_value="todo")`
2. **Start Work** → `manage_task("update", task_id="...", status="doing")`
3. **Research** → Use knowledge base
4. **Implement** → Write code based on research
5. **Review** → `manage_task("update", task_id="...", status="review")`
6. **Next Task** → `find_tasks(filter_by="status", filter_value="todo")`

### RAG Workflow

```bash
# Search knowledge base (2-5 keywords only!)
rag_search_knowledge_base(query="authentication JWT", match_count=5)

# Find code examples
rag_search_code_examples(query="React hooks", match_count=3)
```

---

## Core Commands

### Development
```bash
python formai_server.py      # Start client server (port 5511)
start-python.bat             # Windows with auto-setup
python admin_server.py       # Start admin server (port 5512)
start-admin.bat              # Windows admin server
```

### CSS Development
```bash
npm run build-css            # Build Tailwind CSS once
npm run watch-css            # Watch and rebuild CSS
```

### Testing
```bash
pytest tests/                # Run all tests
pytest tests/ -v             # Verbose output
pytest tests/ --cov=.        # With coverage
```

### Browser Setup
```bash
scripts/install-browser.bat  # Install SeleniumBase browsers
```

---

## Project Structure

```
FormAI/
├── formai_server.py          # Client server (port 5511)
├── admin_server.py           # Admin server (port 5512)
├── selenium_automation.py    # Browser automation engine
├── client_callback.py        # Admin callback system
│
├── web/                      # HTML pages
│   ├── index.html           # Main dashboard
│   ├── profiles.html        # Profile management
│   ├── automation.html      # Automation interface
│   ├── recorder.html        # Recording management
│   ├── settings.html        # Settings page
│   └── admin.html           # Admin monitoring
│
├── static/                   # Static assets
│   ├── css/                 # Stylesheets
│   ├── js/                  # JavaScript modules
│   └── Models.json          # AI model configs
│
├── tools/                    # Automation utilities
│   ├── enhanced_field_mapper.py
│   ├── chrome_recorder_parser.py
│   ├── recording_manager.py
│   └── [35+ tool modules]
│
├── profiles/                 # User profile JSON files
├── recordings/               # Chrome DevTools recordings
├── field_mappings/           # Website field mappings
├── admin_data/               # Admin server data
├── tests/                    # Test files
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md      # System architecture
│   ├── features/            # Feature specs
│   └── bugs/                # Bug analysis
└── .claude/                  # Claude Code config
    ├── security.md          # Security guidelines
    ├── testing.md           # Testing workflow
    ├── api-design.md        # API conventions
    ├── database.md          # Data storage
    ├── standards.md         # Code quality
    ├── Agents/              # Agent templates
    └── commands/            # Custom commands
```

---

## Architecture Overview

FormAI is a **Python-based browser automation platform** with a dual-server architecture.

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
- Central monitoring server for multiple installations
- Receives heartbeats from client installations
- Remote command execution via callback system
- Screenshot collection from clients
- Statistics aggregation

**Admin Callback System** (`client_callback.py`)
- Two-way communication between client and admin
- Heartbeat reporting (5-minute intervals)
- Remote command execution handlers
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

---

## UI/Styling Guidelines

**CRITICAL: Theme-Aware Button Styling**

When creating UI components, follow these styling rules for light/dark mode support:

### Action Buttons (Primary Interactive Elements)
**USE:** `bg-secondary hover:bg-secondary/90 text-secondary-foreground`

```html
<!-- CORRECT: Action buttons -->
<button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md">
    Start Camera
</button>

<!-- WRONG: Will appear white in dark mode -->
<button class="bg-primary hover:bg-primary/90 text-primary-foreground">
    Action Button
</button>
```

### Destructive Actions (Delete, Stop, Cancel)
**USE:** `bg-destructive hover:bg-destructive/90 text-destructive-foreground`

### Status Badges (Fixed Semantic Colors)
**OK to use:** Fixed colors like `bg-green-500`, `bg-red-500` with `text-white`

### Theme Color Reference
- **Light Mode:** `bg-primary` = Dark, `bg-secondary` = Light gray
- **Dark Mode:** `bg-primary` = Light (white buttons!), `bg-secondary` = Dark gray

**Key Takeaway:** `bg-primary` inverts between modes. Use `bg-secondary` for consistent colored buttons.

---

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

**Recordings:**
- `POST /api/recordings/import-chrome` - Import Chrome recording
- `GET /api/recordings` - List all recordings
- `GET /api/recordings/{id}` - Get specific recording
- `DELETE /api/recordings/{id}` - Delete recording
- `POST /api/recordings/{id}/replay` - Replay recording with profile

**Field Mappings:**
- `GET /api/field-mappings` - Get all field mappings
- `POST /api/field-mappings` - Create field mapping

### Admin Server (Port 5512)

- `POST /api/heartbeat` - Receive client heartbeat
- `GET /api/clients` - List registered clients
- `GET /api/stats` - Aggregated statistics
- `POST /api/send_command` - Send command to client(s)
- `GET /api/command_results` - Get command results
- `GET /api/screenshots` - List screenshots

---

## Tool Permissions

| Action | Permission |
|--------|------------|
| Read any file | Allowed |
| Write code files | Allowed |
| Run tests, linters | Allowed |
| Edit .env files | Ask first |
| Delete data files | Ask first |
| Run automation | Ask first |

---

## Verification Standards

**NEVER claim something is working unless you have actually verified it**

- Run the application/tests and confirm no errors
- Check actual outputs and behavior
- If verification fails, report the actual error

---

## Security Guidelines

See @.claude/security.md for comprehensive security guidelines.

Key points:
- Store API keys in environment variables
- Use Pydantic for request validation
- Validate file paths to prevent traversal
- Never expose stack traces to clients

---

## Specialized Context

| Directory | Guide | Purpose |
|-----------|-------|---------|
| `docs/` | [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| `.claude/` | Modular guidelines | Detailed guidelines |
| `.claude/Agents/` | Role files | Agent templates |

### Detailed Guidelines (Imported)

@.claude/security.md - Security best practices (OWASP-based)
@.claude/testing.md - Testing workflow and requirements
@.claude/api-design.md - REST API conventions
@.claude/database.md - JSON data storage guidelines
@.claude/standards.md - Code quality and Python conventions

---

## Environment Variables

```env
# Required
OPENROUTER_API_KEY=         # For AI field mapping

# Optional
ADMIN_URL=                  # Admin server URL for callback
OLLAMA_HOST=                # Local Ollama server
OPENAI_API_KEY=             # OpenAI API access
```

---

## Data Storage

All data stored as JSON files (no database required):

- **Profiles** (`profiles/*.json`) - User profile data
- **Recordings** (`recordings/*.json`) - Chrome DevTools recordings
- **Field Mappings** (`field_mappings/*.json`) - Website-specific mappings
- **Admin Data** (`admin_data/`) - Client registry, commands, screenshots

---

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

### Common Tasks

**Add New API Endpoint:**
1. Add endpoint function to `formai_server.py`
2. Use `@app.get()` or `@app.post()` decorator
3. Define Pydantic model if needed
4. Test with curl or frontend

**Add New Page:**
1. Create HTML file in `web/`
2. Add route in server: `@app.get("/page-name")`
3. Return `FileResponse("web/page-name.html")`
4. Add navigation link in sidebar

---

## Documentation Guidelines

### When to Update Documentation

**MUST update CHANGELOG.md when:**
- Adding a new feature or page
- Removing functionality
- Changing data schema
- Modifying API endpoints
- Fixing significant bugs

**MUST update CLAUDE.md when:**
- Adding new routes (update Project Structure)
- Changing environment variables
- Modifying deployment configuration
- Adding new commands or scripts

**MUST update docs/ARCHITECTURE.md when:**
- Adding new data schemas
- Creating new major modules
- Changing data flows
- Adding new integrations

### Documentation Checklist (After Each Feature)

Before committing, verify:
- [ ] CHANGELOG.md entry added with date and description
- [ ] CLAUDE.md updated if structure changed
- [ ] Feature-specific doc created in docs/features/ if complex
- [ ] Related docs updated

---

## Git Workflow

- Branch from `master` for features: `feature/description`
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`
- PRs require: passing tests, type checks
- Squash commits on merge

---

## Testing Requirements

- **Unit tests**: All business logic
- **Integration tests**: API endpoints
- Run `pytest tests/` before committing
- Minimum 80% coverage for new code

For detailed testing guidelines, see @.claude/testing.md

---

## Quick Start

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Build CSS**: `npm install && npm run build-css`
3. **Start server**: `python formai_server.py` (opens http://localhost:5511)
4. **Create profile**: Use the Profiles page
5. **Import recordings**: Use the Recorder page
6. **Run automation**: Execute recordings with profile data

---

## Important Notes

- **Pure Python** - No Rust in this project
- **Port 5511** - Client server (main automation)
- **Port 5512** - Admin server (monitoring)
- **WebSocket** - Real-time automation updates
- **UC Mode** - Undetected Chrome bypasses bot detection
- **No Database** - All data stored as JSON files
- **SeleniumBase** - Handles browser driver management

---

## Recent Changes

See [CHANGELOG.md](CHANGELOG.md) for full history.

### December 2025
- Adopted project-kit documentation structure
- Added modular `.claude/` guidelines
- Created docs/ARCHITECTURE.md
- Fixed outdated README references

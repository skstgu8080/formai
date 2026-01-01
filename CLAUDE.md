# FormAI

## Project Identity
- **Type**: Python Browser Automation Platform
- **Stack**: Python 3.x, FastAPI, SeleniumBase, Tailwind CSS
- **Ports**: Client 5511, Admin 5512
- **Repository**: Local deployment

---

## Universal Rules

### MUST
- **MUST** explore codebase before making changes
- **MUST** run tests before committing
- **MUST** update CHANGELOG.md after significant changes
- **MUST** use Pydantic for request validation
- **MUST** use sub-agents for complex tasks

### MUST NOT
- **MUST NOT** commit secrets, API keys, or tokens
- **MUST NOT** hardcode file paths
- **MUST NOT** expose stack traces to API responses
- **MUST NOT** bypass input validation

---

## Core Commands

```bash
# Development
python formai_server.py      # Start server (port 5511)
python admin_server.py       # Admin server (port 5512)
pytest tests/                # Run tests
npm run build-css            # Build Tailwind CSS

# CLI Automation
python cli.py sites          # List all sites (292+)
python cli.py profiles       # List profiles
python cli.py fill <site_id> # Fill single site
```

---

## JIT Index (Sub-File Reference)

| Need | File |
|------|------|
| **Python modules index** | [.claude/python-modules.md](.claude/python-modules.md) |
| Architecture overview | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **Field mapping logic** | [.claude/field-mapping.md](.claude/field-mapping.md) |
| **7-phase automation** | [.claude/automation-engine.md](.claude/automation-engine.md) |
| **AI/Ollama integration** | [.claude/ai-integration.md](.claude/ai-integration.md) |
| **CLI commands** | [.claude/cli-usage.md](.claude/cli-usage.md) |
| **Chrome recordings** | [.claude/recording-system.md](.claude/recording-system.md) |
| **Sites management** | [.claude/sites-system.md](.claude/sites-system.md) |
| **Multi-step forms** | [.claude/multistep-forms.md](.claude/multistep-forms.md) |
| **Auto-update system** | [.claude/update-system.md](.claude/update-system.md) |
| **Admin callback** | [.claude/admin-callback.md](.claude/admin-callback.md) |
| API endpoints | [.claude/api-design.md](.claude/api-design.md) |
| Security guidelines | [.claude/security.md](.claude/security.md) |
| Testing workflow | [.claude/testing.md](.claude/testing.md) |
| Database schema | [.claude/database.md](.claude/database.md) |
| Code standards | [.claude/standards.md](.claude/standards.md) |
| UI/button patterns | [.claude/ui-patterns.md](.claude/ui-patterns.md) |
| Version history | [CHANGELOG.md](CHANGELOG.md) |

**Rule**: Check the relevant sub-file before making changes.

---

## Project Structure

```
FormAI/
├── formai_server.py     # Main server (5511)
├── admin_server.py      # Admin server (5512)
├── cli.py               # Headless CLI
├── formai_entry.py      # Entry point with auto-update
├── version.py           # Version info
│
├── core/                # Core modules (callback, jobs, queue)
├── tools/               # 25+ automation tools
├── database/            # SQLite layer
├── build/               # PyInstaller & release scripts
├── scripts/             # Batch/shell scripts
├── web/                 # 7 HTML pages
├── static/              # CSS/JS assets
├── data/                # formai.db runtime
├── sites/               # 292+ site configs
├── docs/                # Architecture docs
├── tests/               # Test suite
└── .claude/             # 18 documentation files
```

---

## Environment Variables

```env
OPENROUTER_API_KEY=      # AI field mapping
TWOCAPTCHA_API_KEY=      # CAPTCHA solving
ADMIN_URL=               # Optional admin callback
OLLAMA_HOST=             # Local Ollama (default: localhost:11434)
```

---

## Data Storage

SQLite database (`data/formai.db`):

| Table | Purpose |
|-------|---------|
| `profiles` | User profiles |
| `sites` | 292+ URLs |
| `domain_mappings` | Learned field mappings |
| `fill_history` | Audit log |

---

## Tool Permissions

| Action | Permission |
|--------|------------|
| Read/Write code | Allowed |
| Run tests | Allowed |
| Edit .env | Ask first |
| Delete data | Ask first |
| Run automation | Ask first |

---

## Git Workflow

- Branch: `feature/description`
- Commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Squash on merge

---

## Quick Start

1. `pip install -r requirements.txt`
2. `ollama pull llama3.2`
3. `npm install && npm run build-css`
4. `python formai_server.py`
5. Open http://localhost:5511

---

## Recent Changes

See [CHANGELOG.md](CHANGELOG.md) for full history.

### December 2025
- Reorganized project structure (build/, scripts/)
- Created 18 documentation files in .claude/
- Slimmed node_modules (removed unused React/Puppeteer)
- SQLite migration complete
- 2Captcha integration in Settings

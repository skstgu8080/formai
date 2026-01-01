# FormAI - System Architecture

> **Last Updated:** 2025-12-31
> **Version:** 1.1.1

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [System Diagram](#system-diagram)
- [7-Phase Pipeline](#7-phase-pipeline)
- [Directory Structure](#directory-structure)
- [Data Storage](#data-storage)
- [API Reference](#api-reference)
- [Detailed Documentation](#detailed-documentation)

---

## Overview

FormAI is a **Python-based browser automation platform** for intelligent form filling.

**Core Concept:**
```
┌─────────────────────────────────────────────────────┐
│              CLIENT PC = THE BODY                    │
│  - Runs browser (SeleniumBase/Playwright)           │
│  - Executes form filling actions                    │
│  - Processes sites at scale                         │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              OLLAMA = THE BRAIN                      │
│  - Analyzes form fields via DOM                     │
│  - Decides what to fill and how                     │
│  - Returns structured mappings                      │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│         FORMAI (localhost:5511) = CONTROL CENTER     │
│  - User selects profile + sites                     │
│  - Launches AI agent                                │
│  - WebSocket for live updates                       │
└─────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, FastAPI, Uvicorn |
| Database | SQLite (`data/formai.db`) |
| Browser | SeleniumBase (UC Mode), Playwright |
| AI | Ollama (local), 2Captcha API |
| Frontend | HTML, JavaScript, Tailwind CSS |
| Real-time | WebSockets |

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
├─────────────────────────────────────────────────────────────────┤
│  WEB UI (5511)              CLI                   API            │
│  • Dashboard                python cli.py         POST /api/*    │
│  • Profiles                 fill <site_id>                       │
│  • Sites                    fill-all                             │
│  • Settings                                                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT SERVER (Port 5511)                     │
├─────────────────────────────────────────────────────────────────┤
│  formai_server.py                                                │
│  ├── FastAPI endpoints                                           │
│  ├── WebSocket hub                                               │
│  └── Static file server                                          │
├─────────────────────────────────────────────────────────────────┤
│  AUTOMATION ENGINES                                              │
│  ├── SeleniumBaseAgent (tools/seleniumbase_agent.py)            │
│  │   └── 7-phase pipeline, UC Mode, AI-powered                  │
│  └── SimpleAutofill (tools/simple_autofill.py)                  │
│      └── Lightweight Playwright, fast forms                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│     SQLite       │  │     Ollama       │  │  Admin Server    │
│  data/formai.db  │  │  localhost:11434 │  │   Port 5512      │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ • profiles       │  │ • Form analysis  │  │ • Monitoring     │
│ • sites          │  │ • Field mapping  │  │ • Remote cmds    │
│ • domain_mappings│  │ • CAPTCHA vision │  │ • Screenshots    │
│ • fill_history   │  │                  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 7-Phase Pipeline

**File:** `tools/seleniumbase_agent.py`

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: NAVIGATE                                               │
│  • SeleniumBase UC Mode (Undetected Chrome)                     │
│  • Bypass Cloudflare, bot detection                             │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2: CLEAR                                                  │
│  • Close popups, modals, cookie banners                         │
│  • Remove overlays blocking form                                │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3: DETECT                                                 │
│  • Layer 1: Load saved mappings (instant)                       │
│  • Layer 2: AI analysis via Ollama (3-5 sec)                    │
│  • Layer 3: Pattern matching fallback                           │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4: FILL                                                   │
│  • Map profile fields → form fields                             │
│  • Handle: text, select, checkbox, password, DOB                │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 5: CAPTCHA                                                │
│  • Detect reCAPTCHA, hCaptcha                                   │
│  • Solve via 2Captcha API or Ollama vision                      │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 6: SUBMIT                                                 │
│  • Find and click submit button                                 │
│  • Handle multi-step forms                                      │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 7: LEARN                                                  │
│  • Save successful mappings to database                         │
│  • "Learn Once, Replay Many"                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
FormAI/
├── formai_server.py          # Main server (port 5511)
├── admin_server.py           # Admin server (port 5512)
├── client_callback.py        # Admin callback system
├── cli.py                    # CLI for headless automation
├── version.py                # Version info (1.1.1)
│
├── database/                 # SQLite layer
│   ├── db.py                # Schema and connections
│   └── repositories.py      # Data access (ProfileRepository, etc.)
│
├── tools/                    # Automation tools
│   ├── seleniumbase_agent.py    # Main 7-phase AI agent
│   ├── simple_autofill.py       # Lightweight Playwright filler
│   ├── field_analyzer.py        # DOM field extraction
│   ├── field_mapping_store.py   # Save/load learned mappings
│   ├── captcha_solver.py        # 2Captcha, vision solving
│   ├── ollama_agent.py          # Ollama API client
│   ├── recording_trainer.py     # Learn from Chrome recordings
│   └── system_monitor.py        # System metrics
│
├── web/                      # HTML pages (7 pages)
│   ├── index.html           # Dashboard
│   ├── profiles.html        # Profile management
│   ├── sites.html           # Sites management (292+)
│   ├── training.html        # Import Chrome recordings
│   ├── jobs.html            # Job queue
│   ├── settings.html        # Settings
│   └── admin.html           # Admin monitoring
│
├── static/
│   ├── css/                 # Tailwind CSS
│   └── js/
│       ├── sidebar.js       # Navigation sidebar
│       ├── system-status.js # Footer status
│       └── theme.js         # Dark/light mode
│
├── data/                     # Runtime data
│   └── formai.db            # SQLite database
│
├── sites/                    # Site definitions (292+)
│
└── .claude/                  # Documentation
    ├── field-mapping.md     # Field extraction logic
    ├── automation-engine.md # 7-phase pipeline
    ├── ai-integration.md    # Ollama, 2Captcha
    └── ...
```

---

## Data Storage

### SQLite Database (`data/formai.db`)

| Table | Purpose |
|-------|---------|
| `profiles` | User profiles (name, email, phone, address...) |
| `sites` | 292+ sites with URLs and field configs |
| `domain_mappings` | Learned field mappings per domain |
| `learned_fields` | Selector → profile_key mappings |
| `fill_history` | Fill operation logs |

### Profile Schema

```sql
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    name TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    password TEXT,
    birthdate TEXT,
    gender TEXT,
    address1 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT,
    company TEXT,
    data JSON,  -- Extra fields
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Domain Mappings Schema

```sql
CREATE TABLE domain_mappings (
    domain TEXT PRIMARY KEY,
    url TEXT,
    mappings JSON NOT NULL,  -- [{selector, profile_field}, ...]
    fields_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## API Reference

### Client Server (Port 5511)

#### Profiles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profiles` | List all profiles |
| GET | `/api/profiles/{id}` | Get specific profile |
| POST | `/api/profiles` | Create profile |
| PUT | `/api/profiles/{id}` | Update profile |
| DELETE | `/api/profiles/{id}` | Delete profile |

#### Automation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/automation/start` | Start automation |
| POST | `/api/automation/stop` | Stop all |
| GET | `/api/status` | Server status |

#### Sites
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sites` | List all sites |
| GET | `/api/sites/{id}` | Get site |
| POST | `/api/sites` | Create site |
| DELETE | `/api/sites/{id}` | Delete site |

#### WebSocket
| Endpoint | Description |
|----------|-------------|
| `WS /ws` | Real-time automation updates |

### Admin Server (Port 5512)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/heartbeat` | Client heartbeat |
| GET | `/api/clients` | List clients |
| POST | `/api/send_command` | Remote command |

---

## Detailed Documentation

For implementation details, see:

| Topic | File |
|-------|------|
| Field Mapping Logic | [.claude/field-mapping.md](../.claude/field-mapping.md) |
| Automation Engine | [.claude/automation-engine.md](../.claude/automation-engine.md) |
| AI Integration | [.claude/ai-integration.md](../.claude/ai-integration.md) |
| API Design | [.claude/api-design.md](../.claude/api-design.md) |
| Security | [.claude/security.md](../.claude/security.md) |
| Testing | [.claude/testing.md](../.claude/testing.md) |
| UI Patterns | [.claude/ui-patterns.md](../.claude/ui-patterns.md) |
| Code Standards | [.claude/standards.md](../.claude/standards.md) |
| Database | [.claude/database.md](../.claude/database.md) |

---

## Performance

| Scenario | Time |
|----------|------|
| Simple form (saved mappings) | 5-10 sec |
| Complex form (AI analysis) | 15-25 sec |
| Multi-step form | 30-45 sec |
| With CAPTCHA | +15-30 sec |

---

## Deployment

### Development
```bash
python formai_server.py  # Port 5511
```

### Production (Executable)
```bash
python build_release.py  # Creates FormAI.exe (~59MB)
```

### Multi-Client with Admin
```
Admin Server (VPS:5512)
    ↑ heartbeat
    │
├── Client 1 (5511)
├── Client 2 (5511)
└── Client N (5511)
```

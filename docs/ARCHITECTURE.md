# FormAI - System Architecture

> **Last Updated:** 2025-12-01
> **Version:** 1.0.0

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [System Diagram](#system-diagram)
- [Directory Structure](#directory-structure)
- [Data Storage Schema](#data-storage-schema)
- [API Reference](#api-reference)
- [Data Flow Diagrams](#data-flow-diagrams)
- [External Integrations](#external-integrations)
- [Deployment Architecture](#deployment-architecture)

---

## Overview

FormAI is a **Python-based browser automation platform** for intelligent form filling with AI-powered field detection.

**Key Features:**
- Dual-server architecture (client + admin monitoring)
- SeleniumBase browser automation with anti-bot bypass
- AI-powered form field mapping
- Chrome recording import and replay
- Real-time progress via WebSocket
- Profile-based form filling

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, FastAPI, Uvicorn |
| Browser Automation | SeleniumBase, Playwright, PyAutoGUI |
| AI Integration | OpenRouter, Ollama, Langchain |
| Frontend | HTML, JavaScript, Tailwind CSS |
| Real-time | WebSockets |
| Data Storage | JSON files |

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FormAI Platform                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                CLIENTS                                       │
├──────────────────────────────┬──────────────────────────────────────────────┤
│        WEB BROWSER           │              API CONSUMERS                    │
│                              │                                              │
│  ┌────────────────────────┐  │  ┌────────────────────────────────────────┐  │
│  │ Dashboard (Port 5511)  │  │  │ REST API Endpoints                     │  │
│  │ • Profiles             │  │  │ • Automation control                   │  │
│  │ • Recordings           │  │  │ • Profile management                   │  │
│  │ • Automation           │  │  │ • Recording import                     │  │
│  │ • Settings             │  │  └────────────────────────────────────────┘  │
│  └────────────────────────┘  │                                              │
└──────────────────────────────┴──────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENT SERVER (Port 5511)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐ │
│  │   FastAPI Server   │  │   WebSocket Hub    │  │   Static File Server   │ │
│  │   formai_server.py │  │   Real-time updates│  │   HTML/CSS/JS          │ │
│  └────────────────────┘  └────────────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐ │
│  │ Profile Manager    │  │ Recording Manager  │  │ Field Mapper           │ │
│  │ CRUD operations    │  │ Import/replay      │  │ AI-powered matching    │ │
│  └────────────────────┘  └────────────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Browser Automation Engine                           │ │
│  │  selenium_automation.py                                                │ │
│  │  • SeleniumBase with UC mode (anti-bot bypass)                        │ │
│  │  • CDP (Chrome DevTools Protocol) support                             │ │
│  │  • Form detection and filling                                          │ │
│  │  • Human-like interaction delays                                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
┌──────────────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│    JSON File Storage     │ │   AI Providers   │ │   Admin Server (5512)    │
├──────────────────────────┤ ├──────────────────┤ ├──────────────────────────┤
│  profiles/               │ │  OpenRouter API  │ │  Client monitoring       │
│  recordings/             │ │  Ollama (local)  │ │  Remote commands         │
│  field_mappings/         │ │  OpenAI          │ │  Screenshot collection   │
│  admin_data/             │ │                  │ │  Statistics aggregation  │
└──────────────────────────┘ └──────────────────┘ └──────────────────────────┘
```

---

## Directory Structure

```
FormAI/
├── formai_server.py          # Main client server (FastAPI, port 5511)
├── admin_server.py           # Admin monitoring server (port 5512)
├── selenium_automation.py    # Browser automation engine
├── client_callback.py        # Admin callback system
│
├── web/                      # HTML pages
│   ├── index.html           # Main dashboard
│   ├── profiles.html        # Profile management
│   ├── automation.html      # Automation interface
│   ├── recorder.html        # Recording management
│   ├── settings.html        # Settings page
│   └── admin.html           # Admin dashboard
│
├── static/                   # Static assets
│   ├── css/
│   │   ├── input.css        # Tailwind source
│   │   └── tailwind.css     # Built CSS
│   ├── js/                  # JavaScript modules
│   └── Models.json          # AI model configs
│
├── tools/                    # Automation utilities
│   ├── enhanced_field_mapper.py
│   ├── chrome_recorder_parser.py
│   ├── recording_manager.py
│   ├── ai_form_filler.py
│   ├── ai_value_replacer.py
│   └── puppeteer_replay_wrapper.py
│
├── profiles/                 # User profile JSON files
├── recordings/               # Chrome DevTools recordings
├── field_mappings/           # Website field mappings
├── admin_data/               # Admin server data
│   ├── clients.json
│   ├── commands.json
│   └── screenshots/
│
├── api_keys/                 # API key configurations
├── tests/                    # Test files
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
└── requirements.txt          # Python dependencies
```

---

## Data Storage Schema

### Profile Schema
```json
{
  "id": "profile-001",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-123-4567",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  },
  "personal": {
    "firstName": "John",
    "lastName": "Doe"
  },
  "created_at": "2025-12-01T10:30:00Z",
  "updated_at": "2025-12-01T10:30:00Z"
}
```

### Recording Schema
```json
{
  "id": "recording-001",
  "title": "Example Form",
  "url": "https://example.com/form",
  "steps": [
    {"type": "navigate", "url": "https://example.com"},
    {"type": "click", "selectors": ["#button"]},
    {"type": "change", "selectors": ["#input"], "value": "{{field}}"}
  ],
  "created_at": "2025-12-01T10:30:00Z"
}
```

### Field Mapping Schema
```json
{
  "domain": "example.com",
  "mappings": [
    {"selector": "#first-name", "profile_field": "firstName"},
    {"selector": "#email", "profile_field": "email"}
  ]
}
```

---

## API Reference

### Client Server (Port 5511)

#### Profile Management
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
| POST | `/api/automation/stop` | Stop all automation |
| POST | `/api/automation/stop/{id}` | Stop specific session |
| GET | `/api/status` | Get server status |

#### Recordings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/recordings` | List recordings |
| GET | `/api/recordings/{id}` | Get recording |
| POST | `/api/recordings/import-chrome` | Import Chrome recording |
| DELETE | `/api/recordings/{id}` | Delete recording |
| POST | `/api/recordings/{id}/replay` | Replay with profile |
| GET | `/api/recordings/{id}/analyze` | Analyze fields |

#### Real-time
| Endpoint | Description |
|----------|-------------|
| `WS /ws` | WebSocket for live updates |

### Admin Server (Port 5512)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/heartbeat` | Receive client heartbeat |
| GET | `/api/clients` | List registered clients |
| GET | `/api/stats` | Aggregated statistics |
| POST | `/api/send_command` | Send command to client |
| GET | `/api/command_results` | Get command results |
| GET | `/api/screenshots` | List screenshots |

---

## Data Flow Diagrams

### Automation Flow
```
User selects profile → User selects recording → Start automation
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────┐
                                    │ Load profile and recording      │
                                    └─────────────────────────────────┘
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────┐
                                    │ Initialize browser (UC mode)    │
                                    └─────────────────────────────────┘
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────┐
                                    │ Execute recording steps         │
                                    │ • Navigate to URL               │
                                    │ • Fill fields with profile data │
                                    │ • Click buttons                 │
                                    └─────────────────────────────────┘
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────┐
                                    │ Send progress via WebSocket     │
                                    └─────────────────────────────────┘
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────┐
                                    │ Complete and cleanup browser    │
                                    └─────────────────────────────────┘
```

### Admin Callback Flow
```
Client Server starts → Initialize callback system
                              │
                              ▼
              ┌───────────────────────────────┐
              │ Send heartbeat to Admin (5min)│◄────────┐
              └───────────────────────────────┘         │
                              │                         │
                              ▼                         │
              ┌───────────────────────────────┐         │
              │ Poll for pending commands     │         │
              └───────────────────────────────┘         │
                              │                         │
                              ▼                         │
              ┌───────────────────────────────┐         │
              │ Execute command if pending    │         │
              └───────────────────────────────┘         │
                              │                         │
                              ▼                         │
              ┌───────────────────────────────┐         │
              │ Send result back to Admin     │─────────┘
              └───────────────────────────────┘
```

---

## External Integrations

### AI Providers
- **OpenRouter API**: Cloud-based LLM for field mapping
- **Ollama**: Local LLM support for offline operation
- **OpenAI**: Alternative cloud provider

### Browser Engines
- **SeleniumBase**: Primary automation with UC mode
- **Playwright**: Alternative browser automation
- **Puppeteer**: Recording replay support

---

## Deployment Architecture

### Single Instance (Default)
```
┌──────────────────────┐
│   User's Machine     │
│  ┌────────────────┐  │
│  │ Client Server  │  │
│  │  Port 5511     │  │
│  └────────────────┘  │
│  ┌────────────────┐  │
│  │ Chrome Browser │  │
│  │ (automation)   │  │
│  └────────────────┘  │
└──────────────────────┘
```

### Multi-Client with Admin
```
┌──────────────────────┐     ┌──────────────────────┐
│   Admin Server       │     │   Client Machine 1   │
│   Port 5512          │◄────│   Port 5511          │
│   • Monitoring       │     └──────────────────────┘
│   • Commands         │
│   • Screenshots      │◄────┌──────────────────────┐
└──────────────────────┘     │   Client Machine 2   │
                             │   Port 5511          │
                             └──────────────────────┘
```

---

## Statistics Summary

| Metric | Count |
|--------|-------|
| HTML Pages | 8 |
| API Endpoints | 25+ |
| Python Modules | 35+ |
| Tool Scripts | 15+ |

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [CHANGELOG.md](../CHANGELOG.md) - Change history
- [docs/features/](./features/) - Feature documentation

---

## Maintenance Notes

### How to Update This Document

1. **Adding new API endpoint**: Add to API Reference section
2. **Adding new integration**: Add to External Integrations
3. **Changing architecture**: Update System Diagram
4. **Adding data schema**: Add to Data Storage Schema

### Review Schedule
- Review monthly for accuracy
- Update immediately after major changes

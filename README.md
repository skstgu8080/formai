# FormAI - Browser Automation Platform

<div align="center">

**Intelligent form automation with AI-powered field detection**

<p>
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-documentation">Documentation</a>
</p>

</div>

---

## Quick Start

Get FormAI running in under 2 minutes:

### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (for CSS building)
- Chrome browser (for automation)
- 4GB RAM minimum

### 1. Install Dependencies

```bash
# Clone repository
git clone https://github.com/skstgu8080/formai.git
cd formai

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies (for Tailwind CSS)
npm install
npm run build-css
```

### 2. Start FormAI

**Windows (Recommended):**
```cmd
start-python.bat
```

**Mac/Linux:**
```bash
python formai_server.py
```

### 3. Access Dashboard

Open http://localhost:5511 in your browser.

| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | http://localhost:5511 | Main automation interface |
| **Admin** (optional) | http://localhost:5512 | Client monitoring |

### 4. Quick Test

1. Open http://localhost:5511
2. Create your first profile with personal information
3. Import a Chrome DevTools recording
4. Run automation to fill forms automatically

---

## Features

### Core Capabilities
- **AI-Powered Field Detection**: Smart form field mapping using AI
- **Anti-Bot Bypass**: SeleniumBase UC mode avoids detection
- **Chrome Recording Import**: Use Chrome DevTools recordings
- **Profile Management**: Reusable profile templates
- **Real-Time Updates**: WebSocket-powered progress tracking
- **Admin Monitoring**: Optional centralized client monitoring

### Browser Automation
- SeleniumBase with Undetected Chrome mode
- CDP (Chrome DevTools Protocol) support
- Human-like interaction delays
- Automatic retry and error recovery

### AI Integration
- OpenRouter API support
- Ollama for local AI
- OpenAI compatibility
- Smart field-to-profile mapping

---

## Architecture

FormAI uses a **dual-server architecture**:

```
┌────────────────────────┐     ┌────────────────────────┐
│   Client Server        │     │   Admin Server         │
│   Port 5511            │     │   Port 5512 (optional) │
│                        │     │                        │
│   • Form automation    │────▶│   • Client monitoring  │
│   • Profile management │     │   • Remote commands    │
│   • Recording replay   │     │   • Statistics         │
│   • WebSocket updates  │     │   • Screenshots        │
└────────────────────────┘     └────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, FastAPI, Uvicorn |
| Browser | SeleniumBase, Playwright |
| AI | OpenRouter, Ollama, Langchain |
| Frontend | HTML, JavaScript, Tailwind CSS |
| Real-time | WebSockets |
| Storage | JSON files (no database) |

---

## Project Structure

```
FormAI/
├── formai_server.py      # Main server (port 5511)
├── admin_server.py       # Admin server (port 5512)
├── selenium_automation.py # Browser automation
├── web/                  # HTML pages
├── static/               # CSS, JS, assets
├── tools/                # Automation utilities
├── profiles/             # User profiles (JSON)
├── recordings/           # Chrome recordings
├── docs/                 # Documentation
└── .claude/              # Development guidelines
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Development guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/AI_PROVIDERS.md](docs/AI_PROVIDERS.md) | AI provider setup |
| [docs/RECORDING_QUICK_REFERENCE.md](docs/RECORDING_QUICK_REFERENCE.md) | Recording guide |

---

## API Reference

### Profile Endpoints
```
GET    /api/profiles          # List all profiles
POST   /api/profiles          # Create profile
GET    /api/profiles/{id}     # Get profile
PUT    /api/profiles/{id}     # Update profile
DELETE /api/profiles/{id}     # Delete profile
```

### Automation Endpoints
```
POST   /api/automation/start  # Start automation
POST   /api/automation/stop   # Stop automation
GET    /api/status            # Server status
WS     /ws                    # Real-time updates
```

### Recording Endpoints
```
GET    /api/recordings                  # List recordings
POST   /api/recordings/import-chrome    # Import Chrome recording
POST   /api/recordings/{id}/replay      # Replay with profile
```

---

## Configuration

### Environment Variables

Create a `.env` file:

```env
# AI Provider (choose one)
OPENROUTER_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
OLLAMA_HOST=http://localhost:11434

# Admin Server (optional)
ADMIN_URL=http://admin-server:5512
```

### AI Providers

| Provider | Setup |
|----------|-------|
| **OpenRouter** | Get API key from [openrouter.ai](https://openrouter.ai) |
| **Ollama** | Install from [ollama.ai](https://ollama.ai), run locally |
| **OpenAI** | Get API key from [platform.openai.com](https://platform.openai.com) |

---

## Development

### Start Development Server

```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Build CSS
npm run build-css

# Start server
python formai_server.py
```

### Watch CSS Changes

```bash
npm run watch-css
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Deployment Options

### Standalone (Default)
Run directly with Python:
```bash
python formai_server.py
```

### Executable Build
Create a single executable:
```bash
build-formai.bat
# Creates FormAI.exe (~160MB)
```

### Multi-Client Setup
1. Run admin server: `python admin_server.py`
2. Configure clients with `ADMIN_URL` in `.env`
3. Monitor all clients from admin dashboard

---

## Troubleshooting

<details>
<summary><b>Server won't start</b></summary>

```bash
# Check if port is in use
netstat -an | findstr :5511

# Kill existing process
taskkill /F /PID <process_id>
```
</details>

<details>
<summary><b>Browser automation fails</b></summary>

- Ensure Chrome is installed
- Try running `scripts/install-browser.bat`
- Check that target website is accessible
</details>

<details>
<summary><b>CSS not updating</b></summary>

```bash
npm run build-css
# Or watch for changes:
npm run watch-css
```
</details>

<details>
<summary><b>AI field mapping not working</b></summary>

- Verify API key in `.env` file
- Check API provider status
- Try Ollama for local AI (no API key needed)
</details>

---

## Security & Privacy

- **Local Storage**: All data stored locally as JSON files
- **No Cloud Transmission**: Your data stays on your machine
- **API Key Protection**: Keys stored in `.env` (gitignored)
- **Isolated Sessions**: Browser sessions are sandboxed

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes following [CLAUDE.md](CLAUDE.md) guidelines
4. Run tests: `pytest tests/`
5. Submit a pull request

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

**FormAI** - Intelligent form automation powered by AI.

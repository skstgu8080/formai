# KprCLi Integration Plan: Gemini CLI Fork + Existing Web Interface

## Overview

Replace the current kprcli repository structure with a Gemini CLI fork while preserving all existing Python automation and web interface functionality.

## Architecture Overview

```
koodosbots/kprcli (GitHub Repo)
├── packages/              # 🆕 Gemini CLI fork (KprCLi)
│   ├── cli/              # Terminal interface with Gemini AI
│   ├── core/             # Core functionality
│   ├── a2a-server/       # Agent-to-Agent server
│   ├── test-utils/       # Testing utilities
│   └── vscode-ide-companion/  # VS Code extension
│
├── web/                  # ✅ KEEP - Existing web interface
│   ├── index.html
│   ├── profiles.html
│   ├── automation.html
│   ├── recorder.html
│   └── settings.html
│
├── static/               # ✅ KEEP - Existing assets
│   ├── css/
│   │   └── tailwind.css
│   └── js/
│       ├── dashboard.js
│       ├── sidebar.js
│       └── theme.js
│
├── formai_server.py      # ✅ KEEP - Python FastAPI server (Port 5511)
├── selenium_automation.py # ✅ KEEP - SeleniumBase automation engine
├── client_callback.py    # ✅ KEEP - Admin callback system
│
├── tools/                # ✅ KEEP - Python utilities
│   ├── chrome_recorder_parser.py
│   ├── profile_replay_engine.py
│   └── enhanced_field_mapper.py
│
├── profiles/             # ✅ KEEP - User profile JSON files
├── recordings/           # ✅ KEEP - Browser recordings
├── field_mappings/       # ✅ KEEP - Form field mappings
│
├── package.json          # 🔄 UPDATE - Root workspace config
├── README.md             # 🔄 UPDATE - New architecture docs
├── .gitignore            # 🔄 UPDATE - Add node_modules
├── requirements.txt      # ✅ KEEP - Python dependencies
└── .kpr/                 # 🆕 NEW - KprCLi config directory

REMOVE:
├── kprcli-cli/           # ❌ DELETE - Replaced by Gemini CLI fork
├── main.go               # ❌ DELETE - Replaced by TypeScript CLI
├── go.mod                # ❌ DELETE - No longer using Go
└── cmd/                  # ❌ DELETE - Go command structure
```

---

## Phase 1: Repository Preparation

### 1.1 Backup Current Repository

**Action Items:**
- Clone current https://github.com/koodosbots/kprcli to backup location
- Create backup branch: `git checkout -b backup-before-cli-integration`
- Document all files to preserve

**Files to Preserve:**
```
web/
static/
formai_server.py
admin_server.py
client_callback.py
selenium_automation.py
tools/
profiles/
recordings/
field_mappings/
requirements.txt
.env.example
README.md (parts of it)
```

### 1.2 Prepare Gemini CLI Fork

**Source:** `C:\Users\jon89\Desktop\KprCLi` (already built and configured)

**Status:**
- ✅ Package names updated to `kprcli`
- ✅ Binary renamed to `kpr`
- ✅ Imports updated
- ✅ Build successful
- ⏳ Need to add FormAI integration

**Verification:**
```bash
cd C:\Users\jon89\Desktop\KprCLi
npm run build  # Should complete successfully
```

### 1.3 Create Merge Directory

**Steps:**
1. Create new directory: `C:\Users\jon89\Desktop\kprcli-merged`
2. Copy Gemini CLI fork contents
3. Copy preserved files from current repo
4. Initialize git repository

---

## Phase 2: FormAI Integration Layer (TypeScript)

### 2.1 Create FormAI Client

**File:** `packages/cli/src/formai/formaiClient.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

export interface Profile {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: string;
  // ... other fields
}

export interface AutomationRequest {
  url: string;
  profileId: string;
  recordingId?: string;
}

export interface ServerStatus {
  status: string;
  uptime: number;
  activeSessions: number;
}

export class FormAIClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:5511') {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: 30000,
    });
  }

  async getStatus(): Promise<ServerStatus> {
    const response = await this.client.get('/api/status');
    return response.data;
  }

  async listProfiles(): Promise<Profile[]> {
    const response = await this.client.get('/api/profiles');
    return response.data;
  }

  async getProfile(id: string): Promise<Profile> {
    const response = await this.client.get(`/api/profiles/${id}`);
    return response.data;
  }

  async startAutomation(request: AutomationRequest): Promise<any> {
    const response = await this.client.post('/api/automation/start', request);
    return response.data;
  }

  async stopAutomation(sessionId?: string): Promise<any> {
    const url = sessionId
      ? `/api/automation/stop/${sessionId}`
      : '/api/automation/stop';
    const response = await this.client.post(url);
    return response.data;
  }

  async importRecording(file: string): Promise<any> {
    const response = await this.client.post('/api/recordings/import-chrome', {
      file
    });
    return response.data;
  }
}

export default FormAIClient;
```

**Dependencies to Add:**
```bash
cd packages/cli
npm install axios
```

### 2.2 Create Server Manager

**File:** `packages/cli/src/formai/serverManager.ts`

```typescript
import { spawn, ChildProcess } from 'child_process';
import { FormAIClient } from './formaiClient';
import { debugLogger } from 'kprcli-core';

export class FormAIServerManager {
  private client: FormAIClient;
  private serverProcess: ChildProcess | null = null;
  private pythonPath: string;

  constructor(
    private serverUrl: string = 'http://localhost:5511',
    private pythonServerPath?: string
  ) {
    this.client = new FormAIClient(serverUrl);
    this.pythonPath = pythonServerPath || this.findPythonServer();
  }

  private findPythonServer(): string {
    // Try common locations
    const possiblePaths = [
      '../Formai/formai_server.py',
      '../../Formai/formai_server.py',
      './formai_server.py',
    ];

    // Return first found path (expand in real implementation)
    return possiblePaths[0];
  }

  async isServerRunning(): Promise<boolean> {
    try {
      await this.client.getStatus();
      return true;
    } catch (error) {
      return false;
    }
  }

  async startServer(): Promise<void> {
    if (await this.isServerRunning()) {
      debugLogger.info('FormAI server already running');
      return;
    }

    debugLogger.info('Starting FormAI server...');

    this.serverProcess = spawn('python', [this.pythonPath], {
      stdio: 'inherit',
    });

    // Wait for server to be ready
    await this.waitForServer();
  }

  private async waitForServer(maxAttempts: number = 30): Promise<void> {
    for (let i = 0; i < maxAttempts; i++) {
      if (await this.isServerRunning()) {
        debugLogger.info('FormAI server started successfully');
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('FormAI server failed to start');
  }

  async stopServer(): Promise<void> {
    if (this.serverProcess) {
      this.serverProcess.kill();
      this.serverProcess = null;
      debugLogger.info('FormAI server stopped');
    }
  }

  getClient(): FormAIClient {
    return this.client;
  }
}
```

### 2.3 Create TypeScript Types

**File:** `packages/cli/src/formai/types.ts`

```typescript
export interface Profile {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  business?: {
    name: string;
    email: string;
    phone: string;
  };
}

export interface Recording {
  id: string;
  name: string;
  url: string;
  steps: RecordingStep[];
  createdAt: string;
}

export interface RecordingStep {
  type: string;
  selector: string;
  value?: string;
  url?: string;
}

export interface AutomationSession {
  sessionId: string;
  url: string;
  profileId: string;
  status: 'running' | 'completed' | 'failed';
  progress: number;
}

export interface ServerConfig {
  formaiServerUrl: string;
  autoStartServer: boolean;
  pythonServerPath: string;
  defaultProfile?: string;
}
```

---

## Phase 3: FormAI Tools for Gemini CLI

### 3.1 Profile Management Tool

**File:** `packages/cli/src/tools/formai/profile-tool.ts`

```typescript
import { FormAIClient } from '../../formai/formaiClient';
import { debugLogger } from 'kprcli-core';

export async function handleProfileCommand(
  action: 'list' | 'get' | 'create' | 'delete',
  args: any,
  client: FormAIClient
): Promise<string> {
  switch (action) {
    case 'list':
      const profiles = await client.listProfiles();
      return formatProfileList(profiles);

    case 'get':
      const profile = await client.getProfile(args.id);
      return formatProfile(profile);

    case 'create':
      // Implementation for creating profile
      return 'Profile created';

    case 'delete':
      // Implementation for deleting profile
      return 'Profile deleted';

    default:
      throw new Error(`Unknown action: ${action}`);
  }
}

function formatProfileList(profiles: any[]): string {
  if (profiles.length === 0) {
    return 'No profiles found. Create one with /profile create';
  }

  let output = 'Available Profiles:\n\n';
  profiles.forEach((profile, index) => {
    output += `${index + 1}. ${profile.name} (${profile.id})\n`;
    output += `   Email: ${profile.email}\n`;
    output += `   Phone: ${profile.phone}\n\n`;
  });

  return output;
}

function formatProfile(profile: any): string {
  return `
Profile: ${profile.name}
ID: ${profile.id}
Email: ${profile.email}
Phone: ${profile.phone}
Address: ${profile.address?.street}, ${profile.address?.city}, ${profile.address?.state} ${profile.address?.zip}
`;
}
```

### 3.2 Automation Tool

**File:** `packages/cli/src/tools/formai/automation-tool.ts`

```typescript
import { FormAIClient } from '../../formai/formaiClient';
import { debugLogger } from 'kprcli-core';

export async function startAutomation(
  url: string,
  profileId: string,
  client: FormAIClient
): Promise<string> {
  try {
    debugLogger.info(`Starting automation for ${url} with profile ${profileId}`);

    const result = await client.startAutomation({
      url,
      profileId,
    });

    return `✅ Automation started successfully!\nSession ID: ${result.sessionId}\nURL: ${url}\nProfile: ${profileId}`;
  } catch (error) {
    debugLogger.error('Automation failed:', error);
    throw new Error(`Failed to start automation: ${error.message}`);
  }
}

export async function stopAutomation(
  sessionId: string | undefined,
  client: FormAIClient
): Promise<string> {
  try {
    await client.stopAutomation(sessionId);
    return sessionId
      ? `Stopped automation session: ${sessionId}`
      : 'Stopped all automation sessions';
  } catch (error) {
    throw new Error(`Failed to stop automation: ${error.message}`);
  }
}
```

### 3.3 Form Filling Tool

**File:** `packages/cli/src/tools/formai/fill-form-tool.ts`

```typescript
import { FormAIClient } from '../../formai/formaiClient';
import { startAutomation } from './automation-tool';

export async function fillForm(
  url: string,
  profileName: string,
  client: FormAIClient
): Promise<string> {
  // Get profile by name
  const profiles = await client.listProfiles();
  const profile = profiles.find(p =>
    p.name.toLowerCase() === profileName.toLowerCase()
  );

  if (!profile) {
    throw new Error(`Profile not found: ${profileName}`);
  }

  return await startAutomation(url, profile.id, client);
}
```

---

## Phase 4: Custom Slash Commands

### 4.1 Add FormAI Commands

**File:** `packages/cli/src/ui/commands/formaiCommands.ts`

```typescript
import { CommandContext, SlashCommand } from './types';
import { FormAIServerManager } from '../../formai/serverManager';
import { handleProfileCommand } from '../../tools/formai/profile-tool';
import { fillForm } from '../../tools/formai/fill-form-tool';

let serverManager: FormAIServerManager;

export function initializeFormAI(config: any): void {
  serverManager = new FormAIServerManager(
    config.formaiServerUrl,
    config.pythonServerPath
  );

  if (config.autoStartServer) {
    serverManager.startServer().catch(console.error);
  }
}

export const profilesCommand: SlashCommand = {
  name: 'profiles',
  description: 'List all profiles',
  async execute(context: CommandContext) {
    const client = serverManager.getClient();
    const output = await handleProfileCommand('list', {}, client);
    context.addMessage({
      role: 'assistant',
      content: output,
    });
  },
};

export const fillCommand: SlashCommand = {
  name: 'fill',
  description: 'Fill form at URL with profile',
  usage: '/fill <url> <profile>',
  async execute(context: CommandContext, args: string[]) {
    if (args.length < 2) {
      throw new Error('Usage: /fill <url> <profile>');
    }

    const [url, ...profileParts] = args;
    const profileName = profileParts.join(' ');

    const client = serverManager.getClient();
    const output = await fillForm(url, profileName, client);

    context.addMessage({
      role: 'assistant',
      content: output,
    });
  },
};

export const serverCommand: SlashCommand = {
  name: 'server',
  description: 'Server control (status/start/stop)',
  usage: '/server <status|start|stop>',
  async execute(context: CommandContext, args: string[]) {
    const action = args[0] || 'status';

    switch (action) {
      case 'status':
        const isRunning = await serverManager.isServerRunning();
        const status = isRunning ? 'Running ✅' : 'Stopped ❌';
        context.addMessage({
          role: 'assistant',
          content: `FormAI Server: ${status}`,
        });
        break;

      case 'start':
        await serverManager.startServer();
        context.addMessage({
          role: 'assistant',
          content: 'FormAI server started ✅',
        });
        break;

      case 'stop':
        await serverManager.stopServer();
        context.addMessage({
          role: 'assistant',
          content: 'FormAI server stopped',
        });
        break;

      default:
        throw new Error('Unknown server command. Use: status, start, or stop');
    }
  },
};

export const webCommand: SlashCommand = {
  name: 'web',
  description: 'Open web UI in browser',
  async execute(context: CommandContext) {
    const open = await import('open');
    await open.default('http://localhost:5511');

    context.addMessage({
      role: 'assistant',
      content: 'Opening web UI at http://localhost:5511',
    });
  },
};
```

### 4.2 Register Commands

**Update:** `packages/cli/src/services/BuiltinCommandLoader.ts`

```typescript
import { profilesCommand, fillCommand, serverCommand, webCommand } from '../ui/commands/formaiCommands';

// Add to existing command registration
export function loadBuiltinCommands(): SlashCommand[] {
  return [
    // ... existing commands
    profilesCommand,
    fillCommand,
    serverCommand,
    webCommand,
  ];
}
```

---

## Phase 5: Configuration & Settings

### 5.1 Default Settings

**File:** `packages/cli/src/config/defaultFormAISettings.ts`

```typescript
export const defaultFormAISettings = {
  formaiServerUrl: 'http://localhost:5511',
  autoStartServer: true,
  pythonServerPath: '',  // Auto-detect if empty
  defaultProfile: '',
};
```

### 5.2 Update Settings Schema

**File:** `packages/cli/src/config/settingsSchema.ts`

Add FormAI settings to schema:

```typescript
export const settingsSchema = {
  // ... existing settings
  formaiServerUrl: {
    type: 'string',
    default: 'http://localhost:5511',
    description: 'FormAI Python server URL',
  },
  autoStartServer: {
    type: 'boolean',
    default: true,
    description: 'Auto-start FormAI server if not running',
  },
  pythonServerPath: {
    type: 'string',
    default: '',
    description: 'Path to formai_server.py (auto-detect if empty)',
  },
  defaultProfile: {
    type: 'string',
    default: '',
    description: 'Default profile ID for automation',
  },
};
```

---

## Phase 6: Update Root Configuration

### 6.1 Root package.json

**File:** `package.json`

```json
{
  "name": "kprcli",
  "version": "0.1.0",
  "description": "AI-powered browser automation with CLI and Web UI",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/koodosbots/kprcli.git"
  },
  "engines": {
    "node": ">=20.0.0"
  },
  "type": "module",
  "workspaces": [
    "packages/*"
  ],
  "private": true,
  "scripts": {
    "start": "cross-env NODE_ENV=development node scripts/start.js",
    "start:cli": "npm run start --workspace packages/cli",
    "start:server": "python formai_server.py",
    "start:admin": "python admin_server.py",
    "build": "node scripts/build.js",
    "build:cli": "npm run build --workspace packages/cli",
    "bundle": "npm run generate && node esbuild.config.js && node scripts/copy_bundle_assets.js",
    "test": "npm run test --workspaces --if-present --parallel",
    "lint": "eslint . --ext .ts,.tsx",
    "clean": "node scripts/clean.js"
  },
  "bin": {
    "kpr": "bundle/kpr.js"
  },
  "keywords": [
    "automation",
    "form-filling",
    "browser-automation",
    "cli",
    "web-ui",
    "gemini",
    "ai"
  ],
  "author": "skstgu8080",
  "license": "Apache-2.0"
}
```

### 6.2 Update .gitignore

**File:** `.gitignore`

```
# Node.js
node_modules/
packages/*/node_modules/
packages/*/dist/
bundle/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# KprCLi
.kpr/
!.kpr/.gitkeep

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# FormAI
profiles/*.json
!profiles/.gitkeep
recordings/*.json
!recordings/.gitkeep
field_mappings/*.json
!field_mappings/.gitkeep
admin_data/
sessions/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

## Phase 7: Documentation Updates

### 7.1 Update README.md

**File:** `README.md`

```markdown
# KprCLi - AI-Powered Browser Automation

**Dual Interface**: CLI (Terminal) + Web UI

[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

KprCLi provides intelligent browser automation with form filling capabilities through two interfaces:
- **CLI**: Gemini-powered terminal interface with natural language commands
- **Web UI**: Visual interface for profile and automation management

Built on [Gemini CLI](https://github.com/google-gemini/gemini-cli) + Python automation engine.

## 🚀 Quick Start

### Install CLI

```bash
npm install -g kprcli
```

### Start Python Server

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start server
python formai_server.py
```

Server runs on http://localhost:5511

### Use CLI

```bash
# Launch KprCLi (auto-starts Python server)
kpr

# Natural language
kpr> Fill out the signup form at example.com using my business profile

# Or direct commands
kpr> /profiles
kpr> /fill https://example.com John
kpr> /web
```

### Use Web UI

Open browser to: http://localhost:5511

## 📦 Installation

### Prerequisites

- Node.js 20+
- Python 3.8+
- Chrome/Chromium

### Full Setup

```bash
# Clone repository
git clone https://github.com/koodosbots/kprcli.git
cd kprcli

# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Build CLI
npm run build

# Link for global use
npm link
```

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│  KprCLi (TypeScript/Node.js)    │
│  - Natural language commands    │
│  - Gemini AI integration        │
│  - Terminal UI                  │
│  - MCP server                   │
└────────┬────────────────────────┘
         │ REST API / WebSocket
┌────────▼────────────────────────┐
│  FormAI Server (Python)         │
│  - SeleniumBase automation      │
│  - Profile management           │
│  - Web UI (port 5511)           │
│  - Recording replay             │
└─────────────────────────────────┘
```

## 🎯 Features

### CLI Features

- **Natural Language**: "Fill signup at example.com with John's profile"
- **Profile Management**: `/profiles` - list, create, edit profiles
- **Automation Control**: `/fill`, `/stop`, `/server`
- **Web UI Integration**: `/web` - open browser interface
- **MCP Support**: Use from other AI tools
- **Gemini Powered**: 1M token context window

### Web UI Features

- Visual profile management
- Form recording and replay
- Real-time automation monitoring
- Chrome DevTools import
- CAPTCHA assistance

## 📖 Usage

### CLI Commands

```bash
# Profiles
/profiles              # List all profiles
/profile create        # Create new profile
/profile edit <id>     # Edit profile

# Automation
/fill <url> <profile>  # Fill form
/stop                  # Stop automation
/server status         # Check server

# Utility
/web                   # Open web UI
/help                  # Show help
```

### Natural Language

```bash
kpr> Fill the job application at indeed.com using my professional profile
kpr> Import my Chrome recording from Downloads
kpr> Stop all running automations
```

### Web UI

1. Open http://localhost:5511
2. Create profiles in Profiles tab
3. Start automation or import recordings
4. Monitor progress in real-time

## ⚙️ Configuration

### CLI Configuration

Located in `~/.kpr/settings.json`:

```json
{
  "formaiServerUrl": "http://localhost:5511",
  "autoStartServer": true,
  "pythonServerPath": "",
  "defaultProfile": "john-business"
}
```

### Server Configuration

Located in `.env`:

```
PORT=5511
ADMIN_URL=http://admin.example.com:5512
GEMINI_API_KEY=your-api-key
```

## 🔌 MCP Integration

Use KprCLi from other AI tools via MCP:

**Gemini CLI:**
```json
{
  "mcpServers": {
    "kpr": {
      "command": "kpr",
      "args": ["mcp"]
    }
  }
}
```

**Usage:**
```bash
gemini> @kpr fill form at example.com with business profile
```

## 🛠️ Development

```bash
# Build CLI
npm run build

# Start development
npm run start:cli

# Start Python server
npm run start:server

# Run tests
npm test

# Lint code
npm run lint
```

## 📁 Project Structure

```
kprcli/
├── packages/              # Gemini CLI fork
│   ├── cli/              # Main CLI package
│   ├── core/             # Core logic
│   └── ...
├── web/                  # Web interface
├── static/               # Assets
├── formai_server.py      # Python server
├── selenium_automation.py # Automation engine
├── tools/                # Python utilities
└── profiles/             # User profiles
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE)

### Attribution

KprCLi is built on [Gemini CLI](https://github.com/google-gemini/gemini-cli) by Google LLC (Apache 2.0).

## 🆘 Support

- **Documentation**: [GitHub Wiki](https://github.com/koodosbots/kprcli/wiki)
- **Issues**: [GitHub Issues](https://github.com/koodosbots/kprcli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/koodosbots/kprcli/discussions)

---

Built with ❤️ using Gemini CLI + Python automation
```

---

## Phase 8: Git Repository Migration

### 8.1 Prepare Merge Directory

```bash
# Create merge directory
mkdir C:\Users\jon89\Desktop\kprcli-merged
cd C:\Users\jon89\Desktop\kprcli-merged

# Copy Gemini CLI fork
cp -r C:\Users\jon89\Desktop\KprCLi/* .

# Copy preserved files from current repo
# (Assuming current repo cloned to C:\Users\jon89\Desktop\kprcli-current)
cp -r C:\Users\jon89\Desktop\Formai/web ./
cp -r C:\Users\jon89\Desktop\Formai/static ./
cp C:\Users\jon89\Desktop\Formai/formai_server.py ./
cp C:\Users\jon89\Desktop\Formai/admin_server.py ./
cp C:\Users\jon89\Desktop\Formai/client_callback.py ./
cp C:\Users\jon89\Desktop\Formai/selenium_automation.py ./
cp -r C:\Users\jon89\Desktop\Formai/tools ./
cp -r C:\Users\jon89\Desktop\Formai/profiles ./
cp -r C:\Users\jon89\Desktop\Formai/recordings ./
cp C:\Users\jon89\Desktop\Formai/requirements.txt ./
cp C:\Users\jon89\Desktop\Formai/.env.example ./
```

### 8.2 Update All Repository References

```bash
# Replace YOUR_USERNAME with koodosbots
find . -type f \( -name "*.json" -o -name "*.md" -o -name "*.ts" \) \
  -exec sed -i 's/YOUR_USERNAME/koodosbots/g' {} +

# Replace YOUR_PUBLISHER_NAME with koodosbots
find . -type f -name "*.json" \
  -exec sed -i 's/YOUR_PUBLISHER_NAME/koodosbots/g' {} +
```

### 8.3 Initialize Git

```bash
cd C:\Users\jon89\Desktop\kprcli-merged

# Initialize git
git init

# Add remote
git remote add origin https://github.com/koodosbots/kprcli.git

# Create .gitignore if not exists
# (Use .gitignore content from Phase 6.2)

# Stage all files
git add .

# Commit
git commit -m "Integrate Gemini CLI fork with FormAI

Major changes:
- Replace Go-based CLI with Gemini CLI fork (TypeScript)
- Add FormAI integration layer for Python server
- Keep existing web interface and Python automation
- Add custom slash commands for FormAI
- Support both CLI and web UI simultaneously

Architecture:
- CLI: Gemini CLI fork (packages/)
- Server: Python/FastAPI (formai_server.py, port 5511)
- Web UI: Existing HTML/JS interface (web/)
- Shared: Profiles, recordings, automation engine

Breaking changes:
- Removed: kprcli-cli/, main.go, go.mod (replaced by packages/)
- Added: Node.js dependencies, TypeScript CLI
- Requires: Node.js 20+ and Python 3.8+

Co-authored-by: Claude <noreply@anthropic.com>"
```

### 8.4 Push to GitHub

**Option 1: Force Push (Complete Replacement)**
```bash
git branch -M main
git push -f origin main
```

**Option 2: New Branch (Safer)**
```bash
git checkout -b cli-integration
git push origin cli-integration
# Then create PR on GitHub
```

---

## Phase 9: NPM Publishing

### 9.1 Prepare CLI Package

```bash
cd packages/cli

# Verify package.json
# - name: "kprcli"
# - version: "0.1.0"
# - description: updated
# - repository: correct
# - bin: "kpr": "dist/index.js"

# Build
npm run build

# Test locally
npm link
kpr --version
```

### 9.2 Publish to NPM

```bash
# Login to npm (if not already)
npm login

# Publish
npm publish --access public

# Verify
npm info kprcli
```

### 9.3 Test Installation

```bash
# Unlink local version
npm unlink -g kprcli

# Install from npm
npm install -g kprcli

# Test
kpr --version
kpr
```

---

## Phase 10: Testing & Verification

### 10.1 CLI Testing

```bash
# Start CLI
kpr

# Test server connection
kpr> /server status

# Test profile listing
kpr> /profiles

# Test natural language
kpr> Show me all my profiles

# Test web UI launch
kpr> /web
```

### 10.2 Web UI Testing

```bash
# Start Python server
python formai_server.py

# Open browser
http://localhost:5511

# Test:
- Profile creation
- Profile editing
- Automation start
- Recording import
```

### 10.3 Integration Testing

```bash
# Terminal 1: Start server
python formai_server.py

# Terminal 2: Use CLI
kpr
> /fill https://example.com john-business

# Browser: Check web UI for active session
http://localhost:5511

# Verify: Both interfaces show same data
```

---

## Post-Integration Tasks

### Documentation

- [ ] Update GitHub README with new architecture
- [ ] Create CLI usage guide
- [ ] Update API documentation
- [ ] Add migration guide for existing users
- [ ] Create video demos

### CI/CD

- [ ] Set up GitHub Actions for TypeScript build
- [ ] Add npm publish workflow
- [ ] Add Python tests
- [ ] Set up automated releases

### Features

- [ ] Add WebSocket progress updates to CLI
- [ ] Enhance natural language parsing with Gemini
- [ ] Build MCP server for cross-tool integration
- [ ] Add CLI-specific commands

---

## Success Criteria

✅ **Phase 1-3:** FormAI integration layer complete
✅ **Phase 4-5:** Custom commands and configuration working
✅ **Phase 6-7:** Repository structure updated and documented
✅ **Phase 8:** Git repository migrated to new structure
✅ **Phase 9:** NPM package published successfully
✅ **Phase 10:** Both CLI and web UI working together

**Final Validation:**
```bash
# Install from npm
npm install -g kprcli

# Start CLI
kpr

# CLI connects to Python server
# Web UI accessible at localhost:5511
# Both interfaces share same data
# Natural language commands work
# All slash commands functional
```

---

## Timeline Estimate

- **Phase 1-2**: 2-3 hours (Repository prep + FormAI client)
- **Phase 3**: 2-3 hours (FormAI tools)
- **Phase 4-5**: 2-3 hours (Commands + configuration)
- **Phase 6-7**: 1-2 hours (Documentation)
- **Phase 8**: 1 hour (Git migration)
- **Phase 9**: 30 mins (NPM publish)
- **Phase 10**: 1-2 hours (Testing)

**Total**: 10-15 hours

---

## Rollback Plan

If issues arise:

```bash
# Restore from backup branch
git checkout backup-before-cli-integration

# Or restore specific files
git checkout backup-before-cli-integration -- web/ static/ *.py

# Force push backup
git push -f origin backup-before-cli-integration:main
```

---

## Contact & Support

- **Repository**: https://github.com/koodosbots/kprcli
- **Issues**: https://github.com/koodosbots/kprcli/issues
- **NPM**: https://www.npmjs.com/package/kprcli

---

**Status**: Ready to execute
**Next Action**: Begin Phase 1 - Repository Preparation

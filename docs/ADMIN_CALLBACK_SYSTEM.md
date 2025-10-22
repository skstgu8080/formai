# FormAI Admin Callback System

## Overview

The FormAI Admin Callback System provides **two-way communication** between your FormAI installations and a central admin server, allowing you to:

- ✅ Monitor all running FormAI instances in real-time
- ✅ View system information (OS, IP, hostname, etc.)
- ✅ Send remote commands to clients
- ✅ Push configuration updates
- ✅ Restart instances remotely
- ✅ Execute custom scripts
- ✅ Download and apply updates

## Architecture

```
┌─────────────────┐          ┌──────────────────┐
│  FormAI Client  │─────────>│   Admin Server   │
│   (Port 5511)   │<─────────│   (Port 5512)    │
└─────────────────┘          └──────────────────┘
     Heartbeat                   Commands
     Status Reports              Control Panel
```

### Components

1. **Admin Server** (`admin_server.py`) - Central monitoring server
2. **Client Callback** (`client_callback.py`) - Client-side communication
3. **Admin Dashboard** (`web/admin.html`) - Web UI for management

## Quick Start

### 1. Start the Admin Server

On your monitoring/admin machine:

```batch
start-admin.bat
```

Or manually:

```bash
python admin_server.py
```

The admin dashboard will be available at: **http://localhost:5512**

### 2. Configure Clients

On each FormAI installation you want to monitor, edit the `.env` file:

```env
# Enable callback system
ADMIN_CALLBACK_URL=http://your-admin-server-ip:5512

# Optional: Change heartbeat interval (default: 300 seconds / 5 minutes)
ADMIN_CALLBACK_INTERVAL=300
```

### 3. Start FormAI Clients

```batch
start-python.bat
```

Clients will automatically register with the admin server and begin sending heartbeats.

## Admin Dashboard Features

### View Connected Clients

- **Real-time status** - Online/offline indicators
- **System info** - Hostname, IP, OS, Python version
- **Last seen** - Time since last heartbeat
- **Statistics** - Total clients, heartbeats, etc.

### Send Commands

#### Quick Commands:
- **🏓 Ping** - Test connectivity
- **📊 Get Status** - Request full system status

#### Custom Commands:
- **Update Config** - Modify `.env` settings remotely
- **Restart** - Restart FormAI instance
- **Execute Script** - Run custom shell commands
- **Download Update** - Pull software updates

### Command Examples

#### 1. Ping a Client
```javascript
// Built-in button - just click "Ping"
```

#### 2. Update Configuration
```json
{
  "config": {
    "LOG_LEVEL": "DEBUG",
    "PROFILES_DIR": "profiles"
  }
}
```

#### 3. Execute Script
```json
{
  "script": "echo Hello from remote client"
}
```

#### 4. Download Update
```json
{
  "url": "http://your-server/updates/formai-v1.1.0.zip"
}
```

## Available Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| `ping` | Test connectivity | None |
| `get_status` | Get full system status | None |
| `update_config` | Update .env configuration | `{"config": {...}}` |
| `restart` | Restart FormAI instance | None |
| `execute_script` | Run shell command | `{"script": "command"}` |
| `download_update` | Download update file | `{"url": "http://..."}` |

## Security Considerations

### Default Setup (Disabled)

By default, the callback system is **disabled** for privacy. Clients will only connect if you explicitly configure `ADMIN_CALLBACK_URL` in their `.env` file.

### Best Practices

1. **Use HTTPS** - In production, use HTTPS for encrypted communication
2. **Firewall Rules** - Restrict admin server access to trusted IPs
3. **Authentication** - Consider adding API keys (future enhancement)
4. **Review Commands** - Be cautious with `execute_script` - it runs with full privileges
5. **Private Network** - Run admin server on a private network

### Command Safety

- ✅ `ping` - Safe
- ✅ `get_status` - Safe (read-only)
- ⚠️ `update_config` - Moderate (can change settings)
- ⚠️ `restart` - Moderate (interrupts service)
- ⚠️ `download_update` - Moderate (downloads files)
- ❌ `execute_script` - **DANGEROUS** (arbitrary code execution)

## Network Configuration

### Local Network Setup

If admin server is on the same network:

```env
ADMIN_CALLBACK_URL=http://192.168.1.100:5512
```

### Remote/Cloud Setup

If admin server is on a VPS or cloud:

```env
ADMIN_CALLBACK_URL=https://admin.yourcompany.com:5512
```

Make sure to:
1. Open port 5512 in firewall
2. Use HTTPS with valid SSL certificate
3. Configure reverse proxy (nginx/Apache) if needed

## Data Storage

The admin server stores data in `admin_data/`:

- `clients.json` - Client registry
- `commands.json` - Pending command queue
- `command_results.json` - Command execution results

## Troubleshooting

### Client Not Showing Up

1. Check `.env` has correct `ADMIN_CALLBACK_URL`
2. Verify admin server is running
3. Check firewall/network connectivity
4. Look for errors in client console

### Commands Not Executing

1. Verify client is online (green status)
2. Check command syntax in dashboard
3. Wait for next heartbeat (max 5 minutes by default)
4. Check client console for error messages

### Admin Server Won't Start

1. Verify port 5512 is not in use: `netstat -an | find "5512"`
2. Check Python dependencies are installed
3. Look for error messages in console

## API Endpoints

For custom integrations, the admin server exposes these REST APIs:

### GET /api/clients
Get all connected clients with status

### GET /api/stats
Get statistics (total clients, online count, etc.)

### POST /api/send_command
Send command to a client
```json
{
  "client_id": "uuid",
  "command": "ping",
  "params": {}
}
```

### POST /api/heartbeat
Receive heartbeat from client (used by clients, not humans)

### POST /api/command_result
Receive command result (used by clients, not humans)

### GET /api/command_results
Get all command execution results

## Future Enhancements

- [ ] WebSocket support for instant command delivery
- [ ] Authentication and authorization
- [ ] Client groups and bulk commands
- [ ] Scheduled commands and automation
- [ ] Alert system for offline clients
- [ ] Command history and audit logs
- [ ] File upload/download
- [ ] Remote log viewing

## Support

For issues or questions:
- Check the main `CLAUDE.md` documentation
- Review `sessions.md` for recent changes
- Submit issues to the project repository

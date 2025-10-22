# Telegram Bot Integration - Future Roadmap

## Overview

This document outlines the planned integration of **Telegram bot control** (`@koodosbots/kprcli`) with the FormAI Admin System as a **complementary control interface** alongside the web dashboard.

**Status:** 📋 Planned for future implementation
**Current Priority:** ✅ Get HTTPS callback system working first

---

## Architecture Vision

### Dual Control Interface

```
┌──────────────────────────────────────────────────┐
│           FormAI Admin Server                     │
│           (app.kprcli.com)                        │
│                                                   │
│  ┌────────────────┐      ┌──────────────────┐   │
│  │  REST API      │      │  Command Queue   │   │
│  │  Port 5512     │      │  System          │   │
│  └────────┬───────┘      └────────┬─────────┘   │
│           │                       │              │
│           │                       │              │
└───────────┼───────────────────────┼──────────────┘
            │                       │
            │                       │
    ┌───────┴────────┐     ┌────────┴──────────┐
    │                │     │                   │
    ▼                ▼     ▼                   ▼
┌─────────┐   ┌──────────────┐      ┌─────────────────┐
│   Web   │   │   Telegram   │      │  Windows        │
│Dashboard│   │     Bot      │      │  Clients        │
│  HTTPS  │   │   @kprcli    │      │  (Heartbeat)    │
└─────────┘   └──────────────┘      └─────────────────┘
```

**Two Control Methods:**
1. **Web Dashboard** (Current) - `https://app.kprcli.com`
2. **Telegram Bot** (Future) - Mobile/chat interface

---

## Why Add Telegram?

### Advantages Over Web Dashboard

✅ **Mobile-First**
- Control from phone anywhere
- No need to open laptop
- Push notifications built-in

✅ **Instant Notifications**
- Real-time alerts for events
- No polling/refreshing needed
- Get notified when clients go offline

✅ **Quick Commands**
- Type `/clients` instead of navigating UI
- Faster for power users
- Chat history = command history

✅ **Multi-User**
- Easy to share bot access
- Different permission levels possible
- Audit trail in chat

### When to Use Each Interface

| Task | Web Dashboard | Telegram Bot |
|------|--------------|--------------|
| View all clients | ⭐⭐⭐ Best visual layout | ⭐⭐ Good for quick check |
| Send quick command | ⭐⭐ Click through UI | ⭐⭐⭐ Type `/ping client123` |
| Get notifications | ⭐ Need to check manually | ⭐⭐⭐ Push alerts |
| Detailed analysis | ⭐⭐⭐ Charts/tables | ⭐ Text-based |
| Mobile use | ⭐⭐ Responsive web | ⭐⭐⭐ Native app feel |
| Command history | ⭐ Need logs | ⭐⭐⭐ Chat scroll |

---

## Planned Bot Commands

### Client Management

```
/clients
  → List all connected clients with status

/client <id>
  → View detailed info for specific client

/online
  → Show only online clients

/offline
  → Show offline clients (potential issues)
```

### Command Execution

```
/ping <client_id>
  → Ping a specific client

/status <client_id>
  → Get full system status

/restart <client_id>
  → Restart FormAI instance

/command <client_id> <command_type>
  → Execute custom command
```

### Automation

```
/autofill <client_id> <url> <profile>
  → Trigger form automation on client

/jobs
  → View active automation jobs

/cancel <job_id>
  → Cancel running job
```

### Notifications (Auto)

```
[AUTO] 🟢 Client "PC-Office" came online
[AUTO] 🔴 Client "PC-Home" went offline (5 min ago)
[AUTO] ✅ Job form-fill-123 completed successfully
[AUTO] ❌ Job form-fill-456 failed: timeout
```

### Statistics

```
/stats
  → Overall statistics (clients, uptime, jobs)

/health
  → System health check

/report
  → Generate activity report
```

---

## Implementation Plan

### Phase 1: Read-Only Bot (Easy)

**Goal:** View clients and status via Telegram

**Tasks:**
1. Add Telegram bot token to admin server config
2. Implement `/clients` command (read from existing API)
3. Implement `/status <client_id>` command
4. Set up webhook or polling for bot updates

**Complexity:** ⭐ Low (mostly API wrapper)

### Phase 2: Command Execution (Medium)

**Goal:** Send commands to clients via Telegram

**Tasks:**
1. Implement `/ping`, `/restart` commands
2. Map to existing command queue system
3. Send results back to Telegram chat
4. Add command history tracking

**Complexity:** ⭐⭐ Medium (reuse existing infra)

### Phase 3: Notifications (Medium)

**Goal:** Push alerts to Telegram

**Tasks:**
1. Detect client connect/disconnect events
2. Send Telegram messages for events
3. Add notification preferences
4. Implement alert rules

**Complexity:** ⭐⭐ Medium (event system needed)

### Phase 4: Automation Triggers (Advanced)

**Goal:** Start form automation from Telegram

**Tasks:**
1. Implement `/autofill` command
2. Profile selection interface
3. Job status tracking
4. Result reporting

**Complexity:** ⭐⭐⭐ High (complex workflows)

---

## Technical Integration

### Option A: Separate Bot Server

```python
# telegram_bot.py
import telebot
import requests

bot = telebot.TeleBot("YOUR_BOT_TOKEN")

@bot.message_handler(commands=['clients'])
def show_clients(message):
    # Call admin API
    response = requests.get("http://localhost:5512/api/clients")
    clients = response.json()

    # Format for Telegram
    text = "📱 Connected Clients:\n\n"
    for client in clients['clients']:
        status = "🟢" if client['is_online'] else "🔴"
        text += f"{status} {client['hostname']}\n"

    bot.reply_to(message, text)

bot.polling()
```

**Pros:**
- Separate codebase
- Easy to maintain
- Can restart independently

**Cons:**
- Another service to manage
- Need to secure internal API

### Option B: Built Into Admin Server

```python
# In admin_server.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

async def clients_command(update: Update, context):
    # Direct access to database
    clients_list = get_all_clients()
    await update.message.reply_text(format_clients(clients_list))

# Add to startup
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(CommandHandler("clients", clients_command))
```

**Pros:**
- Single service
- Direct database access
- Simpler deployment

**Cons:**
- Couples bot to admin server
- More dependencies

### Recommendation: **Option A** (Separate Bot Server)

Cleaner separation, easier to debug, more flexible.

---

## Security Considerations

### Authentication

**Telegram User Whitelist:**
```python
ALLOWED_USERS = [
    123456789,  # Your Telegram user ID
    987654321,  # Team member
]

def is_authorized(user_id):
    return user_id in ALLOWED_USERS
```

**Or Admin Code:**
```
/auth ABC123
  → Authenticate with admin code
  → Bot remembers your Telegram ID
```

### Permission Levels

| Level | Can View | Can Command | Can Trigger Automation |
|-------|----------|-------------|------------------------|
| Viewer | ✅ | ❌ | ❌ |
| Operator | ✅ | ✅ | ❌ |
| Admin | ✅ | ✅ | ✅ |

### Rate Limiting

```python
# Prevent abuse
MAX_COMMANDS_PER_MINUTE = 10
command_count = {}  # user_id -> count
```

---

## Bot Setup Guide (Future)

### 1. Create Telegram Bot

```
1. Message @BotFather on Telegram
2. Send /newbot
3. Follow prompts to name your bot
4. Save bot token
```

### 2. Configure Admin Server

```env
# Add to .env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ADMIN_IDS=123456789,987654321
TELEGRAM_ENABLED=true
```

### 3. Start Bot Service

```bash
# Option A: Separate service
python telegram_bot.py

# Option B: Built-in (auto-starts with admin server)
systemctl restart formai-admin
```

### 4. Link Your Telegram

```
1. Find your bot on Telegram
2. Send /start
3. Send /auth <admin_code>
4. Confirmed! Start using commands
```

---

## Example Telegram Session

```
You:
/start

Bot:
🤖 FormAI Admin Bot

Welcome! To get started, authenticate with:
/auth <admin_code>

Get your admin code from https://app.kprcli.com/settings

──────────────────────

You:
/auth XYZ789

Bot:
✅ Authentication successful!
You now have Admin access.

Try these commands:
• /clients - View connected clients
• /help - Show all commands

──────────────────────

You:
/clients

Bot:
📱 Connected Clients (3 online, 1 offline)

🟢 PC-Office-01
   IP: 192.168.1.100
   Last seen: Just now
   [Ping] [Status] [Restart]

🟢 PC-Home
   IP: 192.168.1.200
   Last seen: 2m ago
   [Ping] [Status] [Restart]

🟢 Laptop-Mobile
   IP: 192.168.1.150
   Last seen: 30s ago
   [Ping] [Status] [Restart]

🔴 Server-Backup
   IP: 192.168.1.50
   Last seen: 2h ago (OFFLINE)

──────────────────────

[Later - Auto notification]

Bot:
🔴 ALERT: Client "Server-Backup" went offline
Time: 14:32 UTC
Last seen: 5 minutes ago
Location: 192.168.1.50

──────────────────────

You:
/ping PC-Office-01

Bot:
⏳ Sending ping to PC-Office-01...
✅ Pong! Response time: 0.3s
Status: Online and healthy
```

---

## NPM Package Integration

### Using Your `@koodosbots/kprcli` Package

```bash
# On VPS, install kprcli globally
npm install -g @koodosbots/kprcli

# Link to your Telegram bot
kprcli login
# Follow prompts to authenticate

# Start agent
kprcli start
```

### How It Would Connect

```javascript
// kprcli polls for jobs from Telegram bot
// When job arrives:
{
  "task": "form_fill",
  "client_id": "12345",
  "url": "https://example.com/form",
  "profile": "john_doe"
}

// kprcli executes by calling FormAI API:
fetch('https://app.kprcli.com/api/send_command', {
  method: 'POST',
  body: JSON.stringify({
    client_id: "12345",
    command: "autofill",
    params: { url: "...", profile: "..." }
  })
})
```

---

## Benefits Summary

### For Admins
- ✅ Mobile control
- ✅ Real-time notifications
- ✅ Quick commands
- ✅ No browser needed

### For Teams
- ✅ Easy collaboration
- ✅ Share access via bot
- ✅ Audit trail in chat
- ✅ Different permission levels

### For Enterprise
- ✅ Integration with chat workflows
- ✅ Automated alerts
- ✅ Command history
- ✅ Multi-user management

---

## Timeline Estimate

### Minimal Bot (Read-Only)
- **Time:** 2-4 hours
- **Features:** View clients, basic commands
- **Value:** Quick mobile access

### Full-Featured Bot
- **Time:** 1-2 days
- **Features:** All commands, notifications, automation
- **Value:** Complete Telegram control

### Enterprise Bot
- **Time:** 1 week
- **Features:** Multi-user, permissions, analytics, webhooks
- **Value:** Team collaboration platform

---

## Current Status

✅ **Web Dashboard** - Production ready at `https://app.kprcli.com`
✅ **Callback System** - Working with HTTPS
✅ **Command Queue** - Infrastructure ready
📋 **Telegram Bot** - Planned (this document)

**Next Steps:**
1. Deploy current system to `https://app.kprcli.com`
2. Test with real clients
3. Stabilize callback system
4. Then implement Telegram bot (Phase 1)

---

## Conclusion

The Telegram bot will be a **powerful addition** to FormAI admin, providing:
- Mobile-first control
- Real-time notifications
- Quick command execution
- Team collaboration features

But the **web dashboard comes first** - it's the foundation. Once that's stable and working with `https://app.kprcli.com`, adding Telegram will be straightforward since the API infrastructure is already there.

**For now:** Focus on getting callback system working perfectly.
**Later:** Add Telegram as complementary interface using existing APIs.

---

📚 **Related Documentation:**
- `FINAL_SETUP_GUIDE.md` - Current system deployment
- `DOMAIN_SSL_SETUP.md` - HTTPS configuration
- `ADMIN_CALLBACK_SYSTEM.md` - Callback architecture
- `APACHE2_DEPLOYMENT.md` - Server setup

---

*This is a planning document. Implementation will begin after the current callback system is fully deployed and stable.*

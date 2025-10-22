# 🚀 FormAI Admin System - Complete Setup Guide

## Your Configuration

**Domain:** `app.kprcli.com`
**VPS IP:** `31.97.100.192`
**Dashboard:** `https://app.kprcli.com` 🔒
**Client URL:** `https://app.kprcli.com` 🔒

---

## 🎯 Complete Setup (3 Steps)

### Step 1: DNS Configuration (5 minutes)

Add A record in your DNS provider:

```
Type: A
Name: app
Value: 31.97.100.192
TTL: 14400
```

**Verify DNS:**
```bash
dig app.kprcli.com
# Should return: 31.97.100.192
```

---

### Step 2: VPS Setup (10 minutes)

```bash
# 1. Upload files from Windows
scp apache2-setup.sh root@31.97.100.192:/root/
scp ssl-setup.sh root@31.97.100.192:/root/
scp admin_server.py root@31.97.100.192:/root/formai-admin/
scp -r web root@31.97.100.192:/root/formai-admin/

# 2. Connect to VPS
ssh root@31.97.100.192

# 3. Run Apache2 setup
chmod +x /root/apache2-setup.sh
bash /root/apache2-setup.sh

# 4. Start FormAI service
systemctl start formai-admin
systemctl enable formai-admin

# 5. Run SSL setup (after DNS propagates)
chmod +x /root/ssl-setup.sh
bash /root/ssl-setup.sh
```

---

### Step 3: Windows Client Setup (2 minutes)

**Edit `.env` file:**
```env
ADMIN_CALLBACK_URL=https://app.kprcli.com
ADMIN_CALLBACK_INTERVAL=300
```

**Start FormAI:**
```batch
start-python.bat
```

---

## ✅ Verification Checklist

### DNS Check
```bash
dig app.kprcli.com  # Returns 31.97.100.192
```

### VPS Check
```bash
systemctl status apache2        # Active (running)
systemctl status formai-admin  # Active (running)
curl https://app.kprcli.com/api/stats  # Returns JSON
```

### Dashboard Check
- Open https://app.kprcli.com in browser
- See 🔒 lock icon (secure)
- Dashboard loads successfully

### Client Check
- FormAI console shows: `📡 Heartbeat sent to admin server`
- Client appears in dashboard
- Status shows "Online" (green)

---

## 🎛️ What You Get

### Professional Setup
- ✅ Custom subdomain (app.kprcli.com)
- ✅ SSL certificate (HTTPS)
- ✅ Apache2 reverse proxy
- ✅ Auto-renewing certificate
- ✅ Security headers
- ✅ Production-ready

### Features
- ✅ Real-time client monitoring
- ✅ Remote command execution
- ✅ Configuration updates
- ✅ System status viewing
- ✅ Restart capabilities
- ✅ Script execution
- ✅ Update downloads

### Security
- ✅ Encrypted communication (HTTPS)
- ✅ Backend not exposed (port 5512 internal)
- ✅ Strong SSL configuration
- ✅ Security headers enabled
- ✅ Auto certificate renewal
- ✅ Modern TLS only

---

## 📊 Architecture

```
Windows Clients
     │
     │ HTTPS Heartbeat
     │ https://app.kprcli.com
     │
     ▼
┌─────────────────────────────┐
│  DNS: app.kprcli.com        │
│  Points to: 31.97.100.192   │
└──────────┬──────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Kali VPS (31.97.100.192)         │
│                                   │
│  ┌────────────────────────────┐  │
│  │  Apache2 (Port 443)        │  │
│  │  - SSL Termination         │  │
│  │  - Reverse Proxy           │  │
│  │  - Security Headers        │  │
│  └──────────┬─────────────────┘  │
│             │                     │
│             ▼                     │
│  ┌────────────────────────────┐  │
│  │  FormAI Admin (Port 5512)  │  │
│  │  - Client Management       │  │
│  │  - Command Queue           │  │
│  │  - Status Tracking         │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

---

## 🔧 Common Commands

### VPS Management

```bash
# Restart services
systemctl restart apache2
systemctl restart formai-admin

# View logs
tail -f /var/log/apache2/formai-admin-error.log
journalctl -u formai-admin -f

# Check SSL
certbot certificates

# Renew SSL (manual)
certbot renew

# Test SSL renewal
certbot renew --dry-run

# Check status
systemctl status apache2
systemctl status formai-admin
systemctl status certbot.timer
```

### Client Management

```batch
REM Windows - Start FormAI
start-python.bat

REM Check .env configuration
type .env | findstr ADMIN
```

### API Testing

```bash
# Get stats
curl https://app.kprcli.com/api/stats

# Get clients
curl https://app.kprcli.com/api/clients

# Send command (requires client_id)
curl -X POST https://app.kprcli.com/api/send_command \
  -H "Content-Type: application/json" \
  -d '{"client_id":"uuid","command":"ping","params":{}}'
```

---

## 🔐 Security Best Practices

### ✅ Implemented
- HTTPS with valid SSL certificate
- Strong TLS configuration (TLS 1.2/1.3 only)
- Security headers (HSTS, X-Frame-Options, etc.)
- Backend hidden (port 5512 internal only)
- Firewall configured properly

### 🎯 Recommended Next Steps
1. **Change SSH port** from 22 to custom port
2. **Install Fail2ban** for brute force protection
3. **Set up log monitoring** (Logwatch, ELK)
4. **Enable Apache ModSecurity** for WAF
5. **Add HTTP authentication** for dashboard
6. **Implement API keys** for client authentication
7. **Set up backups** for admin_data directory
8. **Configure monitoring** (UptimeRobot, Nagios)

---

## 📁 File Structure

### VPS Server (`/root/formai-admin/`)
```
formai-admin/
├── admin_server.py           # Main backend
├── web/
│   └── admin.html            # Dashboard
└── admin_data/
    ├── clients.json          # Client registry
    ├── commands.json         # Command queue
    └── command_results.json  # Execution results
```

### Windows Client
```
C:\Users\jon89\Desktop\Formai\
├── .env                      # Config file
├── formai_server.py          # Main server
├── client_callback.py        # Callback module
├── start-python.bat          # Launcher
└── profiles/                 # User profiles
```

---

## 🚨 Troubleshooting

### DNS Issues
```bash
# Check DNS
dig app.kprcli.com

# Wait for propagation (5 min - 48 hrs)
# Usually takes < 1 hour
```

### SSL Certificate Issues
```bash
# Check certificate
certbot certificates

# Test renewal
certbot renew --dry-run

# View Apache logs
tail -f /var/log/apache2/error.log

# Manual renewal
certbot renew --force-renewal
```

### Client Connection Issues
```bash
# Check services
systemctl status apache2
systemctl status formai-admin

# Test API
curl https://app.kprcli.com/api/stats

# Check firewall
ufw status

# View client attempts
tail -f /var/log/apache2/formai-admin-access.log
```

### Dashboard Not Loading
```bash
# Check Apache config
apache2ctl configtest

# Check internal connection
curl http://localhost:5512/api/stats

# Restart services
systemctl restart formai-admin
systemctl restart apache2
```

---

## 📚 Documentation

1. **DOMAIN_SSL_SETUP.md** - Complete DNS & SSL guide
2. **APACHE2_DEPLOYMENT.md** - Apache2 configuration
3. **ADMIN_CALLBACK_SYSTEM.md** - Admin system features
4. **QUICK_START_ADMIN.md** - Quick reference
5. **CLAUDE.md** - Main project documentation

---

## 🎓 Advanced Topics

### Add Additional Subdomain (api.kprcli.com)

**DNS:**
```
Type: A
Name: api
Value: 31.97.100.192
TTL: 14400
```

**SSL:**
```bash
certbot --apache -d api.kprcli.com
```

### Multiple Domains

```bash
# Add additional domains
certbot --apache -d app.kprcli.com -d example.com -d app.example.com
```

### HTTP Authentication

```bash
# Create password file
htpasswd -c /etc/apache2/.htpasswd admin

# Add to Apache config
<Location />
    AuthType Basic
    AuthName "FormAI Admin"
    AuthUserFile /etc/apache2/.htpasswd
    Require valid-user
</Location>
```

### Rate Limiting

```bash
# Install mod_evasive
apt install libapache2-mod-evasive

# Configure in Apache
<IfModule mod_evasive20.c>
    DOSHashTableSize 3097
    DOSPageCount 5
    DOSSiteCount 100
    DOSPageInterval 1
    DOSSiteInterval 1
    DOSBlockingPeriod 10
</IfModule>
```

---

## 📊 Monitoring Recommendations

### Uptime Monitoring
- **UptimeRobot** (free): https://uptimerobot.com
- **Pingdom**: https://pingdom.com
- **StatusCake**: https://statuscake.com

### SSL Monitoring
- **SSL Labs**: https://www.ssllabs.com/ssltest/
- **SSL Certificate Checker**: https://www.sslshopper.com/ssl-checker.html

### Server Monitoring
```bash
# Install htop
apt install htop

# Monitor resources
htop

# Check disk space
df -h

# Check memory
free -m
```

---

## 💰 Cost Breakdown

### What You're Using (All FREE!)

- ✅ **Domain:** app.kprcli.com subdomain (you own)
- ✅ **VPS:** Kali Linux (you own - 31.97.100.192)
- ✅ **SSL Certificate:** Let's Encrypt (FREE!)
- ✅ **Software:** Apache2, Python, FormAI (FREE!)
- ✅ **Updates:** Automatic (FREE!)

**Total Monthly Cost: $0** 🎉

---

## ✨ What's Next?

### Current System
1. ✅ Set up DNS → **Done**
2. ✅ Configure Apache2 → **Done**
3. ✅ Install SSL certificate → **Done**
4. ✅ Configure clients → **Ready to go!**
5. ⏭️ Monitor and manage clients
6. ⏭️ Send remote commands
7. ⏭️ Push updates
8. ⏭️ Scale to more clients

### Future Enhancements

#### Telegram Bot Control (Planned)
Add mobile control via Telegram bot using `@koodosbots/kprcli`:
- 📱 Control from mobile phone
- 🔔 Real-time push notifications
- ⚡ Quick commands via chat
- 👥 Multi-user access

**Status:** 📋 Documented in `docs/TELEGRAM_INTEGRATION_ROADMAP.md`

**Will Enable:**
- Mobile-first management
- `/clients` - View all clients
- `/ping <client>` - Send commands
- `/status` - Get system health
- Auto-alerts for offline clients

**Timeline:** After current system is stable and tested

---

## 🎉 Success!

Your FormAI Admin System is now:
- 🔒 **Secure** (HTTPS with SSL)
- 🌐 **Professional** (Custom subdomain)
- 🚀 **Production-Ready** (Apache2)
- 🔄 **Automated** (Auto-renewing certificate)
- 📊 **Monitorable** (Real-time dashboard)

**Access your dashboard:** https://app.kprcli.com

**Configure clients with:** `ADMIN_CALLBACK_URL=https://app.kprcli.com`

---

Need help? Check the documentation in `docs/` folder!

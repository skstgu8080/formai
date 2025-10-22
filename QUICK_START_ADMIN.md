# FormAI Admin System - Quick Start

## 🎯 Your VPS Info

- **IP Address:** `31.97.100.192`
- **Web Server:** Apache2 (Port 80)
- **Admin Backend:** Port 5512 (internal only)
- **Dashboard:** http://31.97.100.192

---

## 🚀 VPS Setup (One-Time)

### 1. Upload Files to VPS

```bash
# Upload setup script and files (from your local machine)
scp apache2-setup.sh root@31.97.100.192:/root/
scp admin_server.py root@31.97.100.192:/root/formai-admin/
scp -r web root@31.97.100.192:/root/formai-admin/
```

### 2. Run Apache2 Setup Script

```bash
# Connect to VPS
ssh root@31.97.100.192

# Run setup (installs Apache2, configures reverse proxy)
chmod +x /root/apache2-setup.sh
bash /root/apache2-setup.sh
```

### 3. Start Services

```bash
# Start FormAI Admin service
systemctl start formai-admin
systemctl enable formai-admin

# Apache2 should already be running
systemctl status apache2
systemctl status formai-admin
```

### 4. Verify

```bash
# Test locally on VPS
curl http://localhost/api/stats

# Test from your PC
curl http://31.97.100.192/api/stats

# Should return JSON with client statistics
```

---

## 💻 Client Setup (Each Windows PC)

### 1. Edit `.env` File

Open `C:\Users\jon89\Desktop\Formai\.env` and add:

```env
# Apache2 on port 80 - no port number needed!
ADMIN_CALLBACK_URL=http://31.97.100.192
ADMIN_CALLBACK_INTERVAL=300
```

### 2. Start FormAI

```batch
start-python.bat
```

### 3. Check Console

Look for:
```
✓ Callback system enabled (interval: 300s)
  Admin URL: http://31.97.100.192
📡 Heartbeat sent to admin server
```

---

## 🎛️ Admin Dashboard Usage

### Access Dashboard

Open in any browser:
```
http://31.97.100.192
```

*(Apache2 handles the routing - no port number needed!)*

### Send Commands

1. **Ping** - Test if client is responsive
2. **Get Status** - Request full system info
3. **Custom Command** - Advanced controls

---

## 🔧 Common Commands

### On VPS

```bash
# View FormAI logs
journalctl -u formai-admin -f

# View Apache logs
tail -f /var/log/apache2/formai-admin-access.log
tail -f /var/log/apache2/formai-admin-error.log

# Restart services
systemctl restart formai-admin
systemctl restart apache2

# Check status
systemctl status formai-admin
systemctl status apache2

# View data
cat /root/formai-admin/admin_data/clients.json

# Test API locally
curl http://localhost/api/stats
```

### On Windows Client

```batch
# Start FormAI with callback
start-python.bat

# Check .env configuration
type .env | findstr ADMIN
```

---

## 📊 File Structure

### VPS Server
```
/root/formai-admin/
├── admin_server.py          # Main server
├── web/
│   └── admin.html          # Dashboard
└── admin_data/
    ├── clients.json        # Client registry
    ├── commands.json       # Command queue
    └── command_results.json # Results
```

### Windows Client
```
C:\Users\jon89\Desktop\Formai\
├── .env                    # Config (with ADMIN_CALLBACK_URL)
├── formai_server.py        # Main server (loads callback)
├── client_callback.py      # Callback module
└── start-python.bat        # Launcher
```

---

## ⚡ Quick Troubleshooting

### Client Not Showing in Dashboard

1. Check `.env` has correct URL: `http://31.97.100.192`
2. Verify VPS firewall: `ufw status` (port 80 should be open)
3. Test connectivity: `curl http://31.97.100.192/api/stats`
4. Check Apache is running: `systemctl status apache2`
5. Check FormAI backend: `systemctl status formai-admin`
6. Check client console for errors

### Commands Not Executing

1. Wait up to 5 minutes (next heartbeat)
2. Check client is "Online" (green badge)
3. View Apache logs: `tail -f /var/log/apache2/formai-admin-error.log`
4. View FormAI logs: `journalctl -u formai-admin -f`

### VPS Server Won't Start

1. Check Apache: `systemctl status apache2`
2. Check FormAI: `systemctl status formai-admin`
3. Test internal connection: `curl http://localhost:5512/api/stats`
4. Check logs: `journalctl -u formai-admin -xe`
5. Check Apache config: `apache2ctl configtest`

---

## 🔒 Security Notes

- System is **disabled by default** on clients
- Only enabled when `ADMIN_CALLBACK_URL` is set
- Use HTTPS in production (see `VPS_DEPLOYMENT.md`)
- `execute_script` command is powerful - use carefully
- Consider IP whitelisting for production

---

## 📚 Documentation

- **Apache2 Setup:** `docs/APACHE2_DEPLOYMENT.md` ⭐ **Start here!**
- **Full Admin Guide:** `docs/ADMIN_CALLBACK_SYSTEM.md`
- **VPS Basics:** `docs/VPS_DEPLOYMENT.md`
- **Main Docs:** `CLAUDE.md`

---

## ✅ Setup Checklist

**VPS Setup:**
- [ ] Files uploaded to VPS
- [ ] Apache2 setup script executed
- [ ] Apache2 running
- [ ] FormAI service running
- [ ] Firewall configured (port 80 open)
- [ ] Dashboard accessible at `http://31.97.100.192`

**Client Setup:**
- [ ] `.env` file updated with VPS IP
- [ ] FormAI started
- [ ] Heartbeat sent successfully
- [ ] Client appears in dashboard

**Test:**
- [ ] Send ping command
- [ ] Receive pong response
- [ ] Check client online status

---

🎉 **You're all set!** Your FormAI instances will now report to your Kali VPS at `http://31.97.100.192` via Apache2!

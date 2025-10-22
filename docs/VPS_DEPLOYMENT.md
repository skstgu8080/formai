# FormAI Admin Server - VPS Deployment Guide

## Your Kali Linux VPS Setup

**VPS IP:** `31.97.100.192`
**Admin Port:** `5512`
**Dashboard URL:** `http://31.97.100.192:5512`

## Quick Setup on Kali Linux VPS

### 1. Connect to Your VPS

```bash
ssh root@31.97.100.192
```

### 2. Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3 and pip
apt install python3 python3-pip -y

# Install required packages
pip3 install fastapi uvicorn pydantic colorama
```

### 3. Upload Admin Server Files

**Option A: Using SCP (from your local machine)**

```bash
# Upload admin server
scp admin_server.py root@31.97.100.192:/root/formai-admin/

# Upload admin dashboard
scp web/admin.html root@31.97.100.192:/root/formai-admin/web/
```

**Option B: Using Git (if you have a repo)**

```bash
cd /root
git clone <your-repo-url> formai-admin
cd formai-admin
```

**Option C: Create files manually**

```bash
# Create directories
mkdir -p /root/formai-admin/web
mkdir -p /root/formai-admin/admin_data

# Then copy paste the file contents
nano /root/formai-admin/admin_server.py
nano /root/formai-admin/web/admin.html
```

### 4. Configure Firewall

```bash
# Allow port 5512
ufw allow 5512/tcp

# Check firewall status
ufw status
```

### 5. Start Admin Server

**Option A: Run directly**

```bash
cd /root/formai-admin
python3 admin_server.py
```

**Option B: Run in background with screen**

```bash
# Install screen if not available
apt install screen -y

# Start screen session
screen -S formai-admin

# Run admin server
cd /root/formai-admin
python3 admin_server.py

# Detach: Press Ctrl+A then D
# Reattach later: screen -r formai-admin
```

**Option C: Create systemd service (recommended for production)**

```bash
# Create service file
nano /etc/systemd/system/formai-admin.service
```

Add this content:

```ini
[Unit]
Description=FormAI Admin Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/formai-admin
ExecStart=/usr/bin/python3 /root/formai-admin/admin_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
systemctl daemon-reload
systemctl enable formai-admin
systemctl start formai-admin

# Check status
systemctl status formai-admin

# View logs
journalctl -u formai-admin -f
```

### 6. Verify Server is Running

```bash
# Check if port is open
netstat -tlnp | grep 5512

# Test locally
curl http://localhost:5512/api/stats
```

### 7. Access Dashboard

From any browser:
```
http://31.97.100.192:5512
```

## Client Configuration

On each Windows machine running FormAI:

### 1. Edit `.env` file

```env
ADMIN_CALLBACK_URL=http://31.97.100.192:5512
ADMIN_CALLBACK_INTERVAL=300
```

### 2. Start FormAI

```batch
start-python.bat
```

### 3. Verify Connection

Check the FormAI console for:
```
📡 Heartbeat sent to admin server
```

Check VPS admin server logs for:
```
✓ New client registered: HOSTNAME (192.168.x.x)
```

## Security Hardening (Recommended)

### 1. Use HTTPS with Nginx

```bash
# Install nginx and certbot
apt install nginx certbot python3-certbot-nginx -y

# Create nginx config
nano /etc/nginx/sites-available/formai-admin
```

Add:

```nginx
server {
    listen 80;
    server_name 31.97.100.192;

    location / {
        proxy_pass http://127.0.0.1:5512;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and restart:

```bash
ln -s /etc/nginx/sites-available/formai-admin /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 2. Add Authentication (Future Enhancement)

Consider adding:
- API key authentication
- HTTP basic auth via nginx
- IP whitelist

### 3. Firewall Rules

```bash
# Only allow specific IPs (optional)
ufw delete allow 5512/tcp
ufw allow from 203.0.113.0/24 to any port 5512
```

## Monitoring and Maintenance

### Check Server Status

```bash
systemctl status formai-admin
```

### View Logs

```bash
# If using systemd
journalctl -u formai-admin -f

# If using screen
screen -r formai-admin
```

### Restart Server

```bash
systemctl restart formai-admin
```

### Backup Data

```bash
# Backup client data
cp -r /root/formai-admin/admin_data /root/backups/admin_data-$(date +%Y%m%d)
```

## Troubleshooting

### Clients Not Connecting

1. **Check firewall:**
   ```bash
   ufw status
   netstat -tlnp | grep 5512
   ```

2. **Test from client machine:**
   ```bash
   curl http://31.97.100.192:5512/api/stats
   ```

3. **Check VPS logs:**
   ```bash
   journalctl -u formai-admin -n 50
   ```

### Port Already in Use

```bash
# Find what's using port 5512
lsof -i :5512

# Kill process if needed
kill -9 <PID>
```

### Server Crashes

```bash
# Check logs for errors
journalctl -u formai-admin --since "1 hour ago"

# Check disk space
df -h

# Check memory
free -m
```

## Network Diagram

```
┌──────────────────────┐
│   Windows Client 1   │
│   (Home/Office)      │──┐
└──────────────────────┘  │
                          │
┌──────────────────────┐  │    ┌────────────────────┐
│   Windows Client 2   │──┼───>│  Kali Linux VPS    │
│   (Home/Office)      │  │    │  31.97.100.192     │
└──────────────────────┘  │    │  Port: 5512        │
                          │    └────────────────────┘
┌──────────────────────┐  │              │
│   Windows Client N   │──┘              │
│   (Home/Office)      │                 │
└──────────────────────┘                 ▼
                                   Admin Dashboard
                              http://31.97.100.192:5512
```

## Performance Tips

### For Many Clients (50+)

1. **Increase Python workers:**
   ```python
   # In admin_server.py, change:
   uvicorn.run(app, host="0.0.0.0", port=5512, workers=4)
   ```

2. **Use Redis for storage (optional):**
   ```bash
   apt install redis-server
   pip3 install redis
   ```

3. **Optimize heartbeat interval:**
   - Reduce to 120s for faster updates
   - Increase to 600s to reduce load

### VPS Resource Usage

- **Memory:** ~100MB per instance
- **CPU:** <1% idle, ~5% during command processing
- **Disk:** ~1MB per 100 clients
- **Bandwidth:** ~1KB per heartbeat

## Backup and Recovery

### Auto-Backup Script

```bash
#!/bin/bash
# /root/backup-formai.sh

BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/formai-admin-$DATE.tar.gz /root/formai-admin/admin_data

# Keep only last 7 days
find $BACKUP_DIR -name "formai-admin-*.tar.gz" -mtime +7 -delete
```

Add to crontab:
```bash
crontab -e
# Add: 0 3 * * * /root/backup-formai.sh
```

## Need Help?

- Check main documentation: `CLAUDE.md`
- Review callback system guide: `ADMIN_CALLBACK_SYSTEM.md`
- Check recent changes: `sessions.md`

# FormAI Admin Server - Apache2 Deployment

## Overview

This guide shows how to deploy the FormAI Admin Server behind **Apache2** on your Kali Linux VPS.

**Benefits of Using Apache2:**
- ✅ Standard web server port (80/443)
- ✅ Port 5512 not exposed publicly (more secure)
- ✅ Easy SSL/HTTPS setup later
- ✅ Better logging and monitoring
- ✅ Load balancing ready (if needed)
- ✅ Professional production setup

## Your Configuration

- **VPS IP:** `31.97.100.192`
- **Public Port:** `80` (Apache)
- **Internal Port:** `5512` (FormAI Admin)
- **Dashboard URL:** `http://31.97.100.192`
- **Client URL:** `http://31.97.100.192` (no port needed!)

## Quick Setup (Automated)

### 1. Upload Files to VPS

```bash
# From your local machine
scp apache2-setup.sh root@31.97.100.192:/root/
scp admin_server.py root@31.97.100.192:/root/formai-admin/
scp -r web root@31.97.100.192:/root/formai-admin/
```

### 2. Run Setup Script

```bash
# Connect to VPS
ssh root@31.97.100.192

# Run Apache2 setup
chmod +x /root/apache2-setup.sh
bash /root/apache2-setup.sh
```

### 3. Start Services

```bash
# Start FormAI Admin service
systemctl start formai-admin
systemctl enable formai-admin

# Verify Apache is running
systemctl status apache2
systemctl status formai-admin
```

### 4. Test Setup

```bash
# Test locally
curl http://localhost/api/stats

# Test externally (from your PC)
curl http://31.97.100.192/api/stats
```

## Manual Setup (Step by Step)

### 1. Install Packages

```bash
apt update
apt install -y apache2 python3 python3-pip
pip3 install fastapi uvicorn pydantic colorama httpx python-dotenv
```

### 2. Enable Apache Modules

```bash
a2enmod proxy
a2enmod proxy_http
a2enmod proxy_wstunnel
a2enmod headers
a2enmod rewrite
```

### 3. Create Apache Virtual Host

```bash
nano /etc/apache2/sites-available/formai-admin.conf
```

Add this configuration:

```apache
<VirtualHost *:80>
    ServerName 31.97.100.192
    ServerAdmin admin@formai.local

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/formai-admin-error.log
    CustomLog ${APACHE_LOG_DIR}/formai-admin-access.log combined

    # Proxy settings
    ProxyPreserveHost On
    ProxyRequests Off

    # WebSocket support (for future use)
    ProxyPass /ws ws://127.0.0.1:5512/ws
    ProxyPassReverse /ws ws://127.0.0.1:5512/ws

    # Main proxy - forward all requests to FormAI Admin
    ProxyPass / http://127.0.0.1:5512/
    ProxyPassReverse / http://127.0.0.1:5512/

    # Headers
    RequestHeader set X-Forwarded-Proto "http"
    RequestHeader set X-Forwarded-Port "80"

    # Security headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
</VirtualHost>
```

### 4. Enable Site

```bash
# Disable default site
a2dissite 000-default.conf

# Enable FormAI site
a2ensite formai-admin.conf

# Test configuration
apache2ctl configtest

# Restart Apache
systemctl restart apache2
```

### 5. Create SystemD Service

```bash
nano /etc/systemd/system/formai-admin.service
```

Add:

```ini
[Unit]
Description=FormAI Admin Server
After=network.target apache2.service
Requires=apache2.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/formai-admin
ExecStart=/usr/bin/python3 /root/formai-admin/admin_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable formai-admin
systemctl start formai-admin
```

### 6. Configure Firewall

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable

# Port 5512 is NOT opened - it's only accessible via Apache proxy
```

## Client Configuration

On Windows machines, edit `.env`:

```env
# Use Apache on port 80 (no port number needed!)
ADMIN_CALLBACK_URL=http://31.97.100.192
ADMIN_CALLBACK_INTERVAL=300
```

Start FormAI:
```batch
start-python.bat
```

## How It Works

```
┌──────────────┐
│ Windows PC   │
│ (Client)     │
└──────┬───────┘
       │ Heartbeat to http://31.97.100.192
       │
       ▼
┌──────────────────────────────────────┐
│ Kali VPS (31.97.100.192)             │
│                                       │
│  ┌─────────────┐      ┌────────────┐│
│  │  Apache2    │─────>│  FormAI    ││
│  │  Port 80    │      │  Admin     ││
│  │  (Public)   │<─────│  Port 5512 ││
│  └─────────────┘      │  (Private) ││
│                        └────────────┘│
└──────────────────────────────────────┘
```

**Traffic Flow:**
1. Client sends heartbeat to `http://31.97.100.192` (port 80)
2. Apache receives on port 80
3. Apache forwards to `localhost:5512` (FormAI Admin)
4. FormAI processes and responds
5. Apache returns response to client

## Logging and Monitoring

### Apache Logs

```bash
# Error log
tail -f /var/log/apache2/formai-admin-error.log

# Access log
tail -f /var/log/apache2/formai-admin-access.log
```

### FormAI Admin Logs

```bash
# Service logs
journalctl -u formai-admin -f

# Check status
systemctl status formai-admin
```

### Check Active Connections

```bash
# Apache connections
netstat -an | grep :80

# Internal FormAI connections
netstat -an | grep :5512
```

## SSL/HTTPS Setup (Optional but Recommended)

### Using Let's Encrypt (Free SSL)

```bash
# Install certbot
apt install -y certbot python3-certbot-apache

# Get SSL certificate (if you have a domain)
certbot --apache -d yourdomain.com

# Or for IP-based (self-signed)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/formai-admin.key \
  -out /etc/ssl/certs/formai-admin.crt
```

### Update Apache Config for HTTPS

```bash
nano /etc/apache2/sites-available/formai-admin-ssl.conf
```

```apache
<VirtualHost *:443>
    ServerName 31.97.100.192

    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/formai-admin.crt
    SSLCertificateKeyFile /etc/ssl/private/formai-admin.key

    # Same proxy config as HTTP version
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyPass / http://127.0.0.1:5512/
    ProxyPassReverse / http://127.0.0.1:5512/

    ErrorLog ${APACHE_LOG_DIR}/formai-admin-ssl-error.log
    CustomLog ${APACHE_LOG_DIR}/formai-admin-ssl-access.log combined
</VirtualHost>
```

Enable:
```bash
a2enmod ssl
a2ensite formai-admin-ssl
systemctl restart apache2
```

Update client `.env`:
```env
ADMIN_CALLBACK_URL=https://31.97.100.192
```

## Troubleshooting

### Apache Not Starting

```bash
# Check syntax
apache2ctl configtest

# Check logs
tail -100 /var/log/apache2/error.log

# Check if port 80 is in use
netstat -tlnp | grep :80
```

### 502 Bad Gateway

This means Apache can't reach FormAI Admin on port 5512:

```bash
# Check if FormAI is running
systemctl status formai-admin

# Check if port 5512 is listening
netstat -tlnp | grep 5512

# Start FormAI if not running
systemctl start formai-admin
```

### Clients Can't Connect

```bash
# Check firewall
ufw status

# Test from VPS
curl http://localhost/api/stats

# Test externally
curl http://31.97.100.192/api/stats

# Check Apache access log
tail -f /var/log/apache2/formai-admin-access.log
```

### Performance Issues

```bash
# Increase Apache workers
nano /etc/apache2/mods-available/mpm_prefork.conf

# Adjust:
MaxRequestWorkers 150
MaxConnectionsPerChild 3000
```

## Maintenance

### Restart Services

```bash
# Restart FormAI only
systemctl restart formai-admin

# Restart Apache only
systemctl restart apache2

# Restart both
systemctl restart formai-admin apache2
```

### View All Logs

```bash
# Combined view
tail -f /var/log/apache2/formai-admin-*.log \
         <(journalctl -u formai-admin -f)
```

### Backup Configuration

```bash
# Backup Apache config
cp /etc/apache2/sites-available/formai-admin.conf \
   /root/backups/

# Backup FormAI data
tar -czf /root/backups/formai-admin-data.tar.gz \
         /root/formai-admin/admin_data
```

## Performance Tips

- **Enable Apache caching** for static files
- **Use KeepAlive** for persistent connections
- **Enable compression** for API responses
- **Monitor with `htop`** and adjust resources

## Security Best Practices

1. **Keep updated:** `apt update && apt upgrade`
2. **Use HTTPS:** Install SSL certificate
3. **Firewall rules:** Only open necessary ports
4. **Fail2ban:** Protect against brute force
5. **Monitor logs:** Check for suspicious activity

## Next Steps

- ✅ Set up SSL/HTTPS
- ✅ Configure Fail2ban
- ✅ Set up automatic backups
- ✅ Add authentication layer
- ✅ Configure log rotation

## Support

- Main documentation: `CLAUDE.md`
- Quick start: `QUICK_START_ADMIN.md`
- VPS basics: `VPS_DEPLOYMENT.md`

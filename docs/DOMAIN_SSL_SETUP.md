# FormAI Admin - Domain & SSL Setup Guide

## Your Domain Configuration

**Domain:** `app.kprcli.com`
**VPS IP:** `31.97.100.192`
**Dashboard:** `https://app.kprcli.com`
**Client URL:** `https://app.kprcli.com`

---

## Step 1: DNS Configuration

### Add A Record for Your Subdomain

In your DNS provider (where you registered kprcli.com), add this A record:

```
Type: A
Name: app
Value: 31.97.100.192
TTL: 14400 (or Auto)
```

### Optional: Add WWW Alias

```
Type: A
Name: www.app
Value: 31.97.100.192
TTL: 14400
```

### Verify DNS Propagation

```bash
# From any computer
dig app.kprcli.com
# or
nslookup app.kprcli.com

# Should return: 31.97.100.192
```

**Note:** DNS propagation can take 5 minutes to 48 hours (usually < 1 hour)

---

## Step 2: VPS Setup (Apache2)

### 1. Run Apache2 Setup First

```bash
# Upload files
scp apache2-setup.sh root@31.97.100.192:/root/
scp admin_server.py root@31.97.100.192:/root/formai-admin/
scp -r web root@31.97.100.192:/root/formai-admin/

# Connect to VPS
ssh root@31.97.100.192

# Run Apache setup
chmod +x /root/apache2-setup.sh
bash /root/apache2-setup.sh

# Start service
systemctl start formai-admin
systemctl enable formai-admin
```

### 2. Verify HTTP Works

```bash
# Test locally
curl http://localhost/api/stats

# Test from your PC
curl http://app.kprcli.com/api/stats
# or
curl http://31.97.100.192/api/stats
```

If this works, proceed to SSL setup.

---

## Step 3: SSL Certificate Setup (Let's Encrypt)

### Automated SSL Setup

```bash
# Upload SSL setup script
scp ssl-setup.sh root@31.97.100.192:/root/

# Connect to VPS
ssh root@31.97.100.192

# Run SSL setup
chmod +x /root/ssl-setup.sh
bash /root/ssl-setup.sh
```

The script will:
- ✅ Check DNS configuration
- ✅ Install Certbot
- ✅ Update Apache for domain
- ✅ Request free SSL certificate
- ✅ Configure HTTPS
- ✅ Set up auto-renewal
- ✅ Add security headers

### What Happens

1. **DNS Check:** Verifies app.kprcli.com points to your VPS
2. **Certificate Request:** Let's Encrypt validates domain ownership
3. **Auto-Configuration:** Apache automatically configured for HTTPS
4. **HTTP → HTTPS:** All HTTP traffic redirected to HTTPS
5. **Auto-Renewal:** Certificate renews automatically every 90 days

---

## Step 4: Verify HTTPS

### Test HTTPS Connection

```bash
# From your PC
curl https://app.kprcli.com/api/stats

# Should return JSON with no SSL errors
```

### Access Dashboard

Open in browser:
```
https://app.kprcli.com
```

You should see:
- 🔒 Padlock icon (secure connection)
- Valid SSL certificate
- FormAI Admin Dashboard

---

## Step 5: Configure Windows Clients

### Update .env File

On each Windows machine running FormAI:

```env
# Use HTTPS with subdomain
ADMIN_CALLBACK_URL=https://app.kprcli.com
ADMIN_CALLBACK_INTERVAL=300
```

### Restart FormAI

```batch
start-python.bat
```

### Verify Connection

Check FormAI console for:
```
✓ Callback system enabled (interval: 300s)
  Admin URL: https://app.kprcli.com
📡 Heartbeat sent to admin server
```

---

## How It Works

```
┌──────────────────┐
│ Windows Client   │
└────────┬─────────┘
         │
         │ HTTPS Request
         │ https://app.kprcli.com
         │
         ▼
    ┌─────────┐
    │   DNS   │ Resolves to
    └────┬────┘ 31.97.100.192
         │
         ▼
┌─────────────────────────────────────┐
│ Kali VPS (31.97.100.192)            │
│                                      │
│  ┌────────────┐   ┌──────────────┐ │
│  │  Apache2   │──>│  FormAI      │ │
│  │  Port 443  │   │  Admin       │ │
│  │  (HTTPS)   │<──│  Port 5512   │ │
│  │  SSL/TLS   │   │  (Internal)  │ │
│  └────────────┘   └──────────────┘ │
│                                      │
│  Let's Encrypt Certificate           │
└─────────────────────────────────────┘
```

---

## SSL Certificate Management

### View Certificate Information

```bash
certbot certificates
```

### Manual Renewal (Usually Not Needed)

```bash
certbot renew
```

### Test Renewal

```bash
certbot renew --dry-run
```

### Auto-Renewal Status

```bash
systemctl status certbot.timer
```

### Certificate Location

```bash
/etc/letsencrypt/live/app.kprcli.com/
├── cert.pem       # Certificate
├── chain.pem      # Chain file
├── fullchain.pem  # Full chain
└── privkey.pem    # Private key
```

---

## Firewall Configuration

```bash
# Required ports
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (redirects to HTTPS)
ufw allow 443/tcp  # HTTPS
ufw enable
```

Port 5512 is **NOT** opened - it's internal only!

---

## Security Features

### Enabled Security Headers

- ✅ **HSTS:** Forces HTTPS for 1 year
- ✅ **X-Frame-Options:** Prevents clickjacking
- ✅ **X-Content-Type-Options:** Prevents MIME sniffing
- ✅ **X-XSS-Protection:** Cross-site scripting protection
- ✅ **Referrer-Policy:** Controls referrer information

### SSL Configuration

- ✅ **TLS 1.2/1.3 Only:** Old protocols disabled
- ✅ **Strong Ciphers:** Modern encryption only
- ✅ **Perfect Forward Secrecy:** Enhanced security

### Test SSL Configuration

```bash
# SSL Labs test (from browser)
https://www.ssllabs.com/ssltest/analyze.html?d=app.kprcli.com
```

Should get **A or A+ rating**

---

## Troubleshooting

### DNS Not Resolving

```bash
# Check DNS
dig app.kprcli.com
nslookup app.kprcli.com

# Wait for propagation (up to 48 hours, usually < 1 hour)
```

### Certificate Request Fails

**Error:** "DNS problem: NXDOMAIN"
- DNS not configured or not propagated yet
- Wait and try again

**Error:** "Connection refused"
- Port 80 blocked by firewall
- Run: `ufw allow 80/tcp`

**Error:** "Too many requests"
- Hit Let's Encrypt rate limit
- Wait 1 hour and try again

### HTTPS Not Working

```bash
# Check Apache
systemctl status apache2

# Check SSL config
apache2ctl configtest

# Check certificate
certbot certificates

# View logs
tail -f /var/log/apache2/error.log
```

### Certificate Renewal Fails

```bash
# Test renewal
certbot renew --dry-run

# Check timer
systemctl status certbot.timer

# Manual renewal
certbot renew --force-renewal
```

---

## Advanced Configuration

### Add Additional Subdomain (Optional)

For example, adding an API subdomain:

**DNS:**
```
Type: A
Name: api
Value: 31.97.100.192
TTL: 14400
```

**Apache Config:**
```apache
ServerName api.kprcli.com
ServerAlias api.kprcli.com
```

**Client Config:**
```env
ADMIN_CALLBACK_URL=https://api.kprcli.com
```

### Custom SSL Certificate

If you have your own certificate:

```bash
# Copy certificates
cp your-cert.crt /etc/ssl/certs/
cp your-key.key /etc/ssl/private/

# Update Apache config
SSLCertificateFile /etc/ssl/certs/your-cert.crt
SSLCertificateKeyFile /etc/ssl/private/your-key.key
```

---

## Benefits of Using Domain + SSL

### vs IP Address (http://31.97.100.192)

✅ **Professional:** `https://app.kprcli.com` looks better
✅ **Secure:** Encrypted HTTPS connection
✅ **Trustworthy:** Valid SSL certificate
✅ **Memorable:** Easy to remember
✅ **Flexible:** Can change IP without updating clients

### vs IP Address + Port (http://31.97.100.192:5512)

✅ **Clean URLs:** No port numbers
✅ **Firewall Friendly:** Standard HTTPS port (443)
✅ **Corporate Networks:** Not blocked by firewalls
✅ **Mobile Friendly:** Works on all devices

---

## Monitoring

### Check Certificate Expiry

```bash
# Days until expiry
echo | openssl s_client -servername app.kprcli.com -connect app.kprcli.com:443 2>/dev/null | openssl x509 -noout -dates
```

### Monitor Renewal

```bash
# Check last renewal
journalctl -u certbot.timer -n 50
```

### Set Up Alerts (Optional)

```bash
# Install monitoring tool
apt install monitoring-plugins-basic

# Or use external service
# - UptimeRobot
# - Pingdom
# - StatusCake
```

---

## Quick Reference

### Essential URLs

- **Dashboard:** https://app.kprcli.com
- **API Stats:** https://app.kprcli.com/api/stats
- **API Clients:** https://app.kprcli.com/api/clients

### Essential Commands

```bash
# Restart services
systemctl restart apache2
systemctl restart formai-admin

# Check SSL
certbot certificates

# Renew SSL
certbot renew

# View logs
tail -f /var/log/apache2/formai-admin-error.log
journalctl -u formai-admin -f
```

### Client Configuration

```env
ADMIN_CALLBACK_URL=https://app.kprcli.com
ADMIN_CALLBACK_INTERVAL=300
```

---

## Support Resources

- **Apache2 Guide:** `APACHE2_DEPLOYMENT.md`
- **Quick Start:** `QUICK_START_ADMIN.md`
- **Admin System:** `ADMIN_CALLBACK_SYSTEM.md`
- **Main Docs:** `CLAUDE.md`

---

## Certificate Renewal Timeline

- **Day 0:** Certificate issued (valid 90 days)
- **Day 60:** Auto-renewal attempt #1
- **Day 70:** Auto-renewal attempt #2 (if #1 failed)
- **Day 80:** Auto-renewal attempt #3 (if #2 failed)
- **Day 88:** Manual intervention needed if all auto-renewals failed

**Certbot checks twice daily and renews when < 30 days remain**

---

🎉 **Your admin system is now professional, secure, and production-ready!**

All clients connect via: **https://app.kprcli.com**

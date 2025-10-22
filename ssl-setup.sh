#!/bin/bash
# FormAI Admin - SSL/HTTPS Setup with Let's Encrypt
# Run this AFTER apache2-setup.sh has been completed

set -e

DOMAIN="app.kprcli.com"
EMAIL="admin@kprcli.com"  # Change this to your email

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      FormAI Admin - SSL/HTTPS Setup                 ║${NC}"
echo -e "${CYAN}║      Domain: app.kprcli.com                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if Apache is running
if ! systemctl is-active --quiet apache2; then
    echo -e "${RED}✗ Apache2 is not running. Please run apache2-setup.sh first${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/6]${NC} Checking DNS configuration..."
echo -e "${CYAN}ℹ Verifying that app.kprcli.com points to this server...${NC}"

# Get server IP
SERVER_IP=$(curl -s ifconfig.me)
echo -e "${CYAN}  Server IP: ${SERVER_IP}${NC}"

# Resolve domain
DOMAIN_IP=$(dig +short ${DOMAIN} | tail -n1)
echo -e "${CYAN}  Domain IP: ${DOMAIN_IP}${NC}"

if [ "${SERVER_IP}" != "${DOMAIN_IP}" ]; then
    echo -e "${YELLOW}⚠ Warning: Domain does not point to this server${NC}"
    echo -e "${YELLOW}  Please add an A record:${NC}"
    echo -e "${YELLOW}  app.kprcli.com → ${SERVER_IP}${NC}"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}[2/6]${NC} Installing Certbot..."
apt update
apt install -y certbot python3-certbot-apache

echo -e "${YELLOW}[3/6]${NC} Updating Apache configuration for domain..."

# Update Apache config to use domain name
cat > /etc/apache2/sites-available/formai-admin.conf << 'EOF'
<VirtualHost *:80>
    ServerName app.kprcli.com
    ServerAlias www.app.kprcli.com
    ServerAdmin admin@kprcli.com

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/formai-admin-error.log
    CustomLog ${APACHE_LOG_DIR}/formai-admin-access.log combined

    # Proxy settings
    ProxyPreserveHost On
    ProxyRequests Off

    # WebSocket support
    ProxyPass /ws ws://127.0.0.1:5512/ws
    ProxyPassReverse /ws ws://127.0.0.1:5512/ws

    # Main proxy
    ProxyPass / http://127.0.0.1:5512/
    ProxyPassReverse / http://127.0.0.1:5512/

    # Headers
    RequestHeader set X-Forwarded-Proto "http"
    RequestHeader set X-Forwarded-Port "80"

    # Redirect to HTTPS (will be added after certificate)
    # RewriteEngine on
    # RewriteCond %{SERVER_NAME} =app.kprcli.com [OR]
    # RewriteCond %{SERVER_NAME} =www.app.kprcli.com
    # RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>
EOF

# Reload Apache
systemctl reload apache2

echo -e "${YELLOW}[4/6]${NC} Obtaining SSL certificate from Let's Encrypt..."
echo -e "${CYAN}ℹ This will request a free SSL certificate for app.kprcli.com${NC}"
echo ""

# Request certificate
certbot --apache \
    --non-interactive \
    --agree-tos \
    --email ${EMAIL} \
    --domains ${DOMAIN},www.${DOMAIN} \
    --redirect

echo -e "${YELLOW}[5/6]${NC} Configuring security headers..."

# Add SSL configuration enhancements
cat > /etc/apache2/conf-available/ssl-security.conf << 'EOF'
# SSL Security Configuration
SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
SSLHonorCipherOrder off
SSLSessionTickets off

# HSTS (HTTP Strict Transport Security)
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"

# Additional Security Headers
Header always set X-Frame-Options "SAMEORIGIN"
Header always set X-Content-Type-Options "nosniff"
Header always set X-XSS-Protection "1; mode=block"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
EOF

a2enconf ssl-security
systemctl reload apache2

echo -e "${YELLOW}[6/6]${NC} Setting up automatic renewal..."

# Certbot auto-renewal is already configured via systemd timer
systemctl enable certbot.timer
systemctl start certbot.timer

# Test renewal
echo -e "${CYAN}ℹ Testing certificate renewal...${NC}"
certbot renew --dry-run

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              SSL Setup Complete!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ SSL Certificate installed successfully${NC}"
echo -e "${GREEN}✓ HTTPS enabled for app.kprcli.com${NC}"
echo -e "${GREEN}✓ HTTP automatically redirects to HTTPS${NC}"
echo -e "${GREEN}✓ Auto-renewal configured${NC}"
echo ""
echo -e "${CYAN}Dashboard URLs:${NC}"
echo -e "  ${GREEN}https://app.kprcli.com${NC}"
echo -e "  ${GREEN}https://www.app.kprcli.com${NC}"
echo ""
echo -e "${CYAN}Client Configuration:${NC}"
echo -e "  Update ${YELLOW}.env${NC} file on Windows clients:"
echo -e "  ${GREEN}ADMIN_CALLBACK_URL=https://app.kprcli.com${NC}"
echo ""
echo -e "${CYAN}Certificate Information:${NC}"
certbot certificates
echo ""
echo -e "${CYAN}Renewal Status:${NC}"
systemctl status certbot.timer --no-pager
echo ""
echo -e "${YELLOW}Note: Certificate will auto-renew every 90 days${NC}"
echo ""

#!/bin/bash
# FormAI Admin Server - Apache2 Setup Script
# Run this on your Kali Linux VPS (31.97.100.192)

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║   FormAI Admin Server - Apache2 Setup Script        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/8]${NC} Updating system..."
apt update

echo -e "${YELLOW}[2/8]${NC} Installing required packages..."
apt install -y apache2 python3 python3-pip screen ufw

echo -e "${YELLOW}[3/8]${NC} Installing Python packages..."
pip3 install fastapi uvicorn pydantic colorama httpx python-dotenv

echo -e "${YELLOW}[4/8]${NC} Enabling Apache2 modules..."
a2enmod proxy
a2enmod proxy_http
a2enmod proxy_wstunnel
a2enmod headers
a2enmod rewrite

echo -e "${YELLOW}[5/8]${NC} Creating directories..."
mkdir -p /root/formai-admin/web
mkdir -p /root/formai-admin/admin_data

echo -e "${YELLOW}[6/8]${NC} Creating Apache2 virtual host configuration..."
cat > /etc/apache2/sites-available/formai-admin.conf << 'EOF'
<VirtualHost *:80>
    ServerName app.kprcli.com
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
</VirtualHost>
EOF

echo -e "${YELLOW}[7/8]${NC} Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo -e "${CYAN}ℹ Port 5512 will be blocked externally (only accessible via Apache proxy)${NC}"

echo -e "${YELLOW}[8/8]${NC} Creating systemd service for FormAI Admin..."
cat > /etc/systemd/system/formai-admin.service << 'EOF'
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
EOF

# Enable Apache site
a2dissite 000-default.conf
a2ensite formai-admin.conf

# Reload systemd and Apache
systemctl daemon-reload
systemctl restart apache2

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Apache2 Setup Complete!                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "  1. Upload FormAI files to /root/formai-admin/"
echo -e "     ${CYAN}scp admin_server.py root@31.97.100.192:/root/formai-admin/${NC}"
echo -e "     ${CYAN}scp -r web root@31.97.100.192:/root/formai-admin/${NC}"
echo ""
echo -e "  2. Start the FormAI service:"
echo -e "     ${GREEN}systemctl start formai-admin${NC}"
echo -e "     ${GREEN}systemctl enable formai-admin${NC}"
echo ""
echo -e "  3. Check status:"
echo -e "     ${GREEN}systemctl status formai-admin${NC}"
echo -e "     ${GREEN}systemctl status apache2${NC}"
echo ""
echo -e "  4. View logs:"
echo -e "     ${CYAN}journalctl -u formai-admin -f${NC}"
echo -e "     ${CYAN}tail -f /var/log/apache2/formai-admin-error.log${NC}"
echo ""
echo -e "  5. Access dashboard via Apache:"
echo -e "     ${GREEN}http://app.kprcli.com${NC} (after DNS propagates)"
echo -e "     ${GREEN}http://31.97.100.192${NC} (immediate access via IP)"
echo ""
echo -e "  6. Configure clients to use (after SSL setup):"
echo -e "     ${GREEN}ADMIN_CALLBACK_URL=https://app.kprcli.com${NC}"
echo -e "     ${CYAN}(Note: No port number needed - Apache handles routing!)${NC}"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo -e "  • Port 5512 is NOT exposed externally (safer)"
echo -e "  • All traffic goes through Apache on port 80"
echo -e "  • Ready for SSL/HTTPS upgrade later"
echo ""

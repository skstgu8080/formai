#!/bin/bash
# FormAI Admin Server - VPS Setup Script
# Run this on your Kali Linux VPS (31.97.100.192)

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║      FormAI Admin Server - VPS Setup Script         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/6]${NC} Updating system..."
apt update && apt upgrade -y

echo -e "${YELLOW}[2/6]${NC} Installing Python and dependencies..."
apt install -y python3 python3-pip screen ufw

echo -e "${YELLOW}[3/6]${NC} Installing Python packages..."
pip3 install fastapi uvicorn pydantic colorama httpx

echo -e "${YELLOW}[4/6]${NC} Creating directories..."
mkdir -p /root/formai-admin/web
mkdir -p /root/formai-admin/admin_data

echo -e "${YELLOW}[5/6]${NC} Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 5512/tcp
ufw status

echo -e "${YELLOW}[6/6]${NC} Creating systemd service..."
cat > /etc/systemd/system/formai-admin.service << 'EOF'
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
EOF

systemctl daemon-reload

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Setup Complete!                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Upload files to /root/formai-admin/"
echo -e "     - admin_server.py"
echo -e "     - web/admin.html"
echo ""
echo -e "  2. Start the service:"
echo -e "     ${GREEN}systemctl start formai-admin${NC}"
echo ""
echo -e "  3. Check status:"
echo -e "     ${GREEN}systemctl status formai-admin${NC}"
echo ""
echo -e "  4. Access dashboard:"
echo -e "     ${GREEN}http://31.97.100.192:5512${NC}"
echo ""
echo -e "  5. Configure clients to use:"
echo -e "     ${GREEN}ADMIN_CALLBACK_URL=http://31.97.100.192:5512${NC}"
echo ""

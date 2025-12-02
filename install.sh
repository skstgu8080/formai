#!/bin/bash
# FormAI Installer for macOS and Linux
# Usage: curl -sSL https://raw.githubusercontent.com/KoodosBots/formai/master/install.sh | bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$HOME/.formai"
GITHUB_REPO="skstgu8080/formai"
VERSION="${FORMAI_VERSION:-latest}"

# Print banner
print_banner() {
    echo ""
    echo -e "${CYAN}  ╔═══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}  ║${NC}         ${GREEN}FormAI Installer${NC}              ${CYAN}║${NC}"
    echo -e "${CYAN}  ╚═══════════════════════════════════════╝${NC}"
    echo ""
}

# Detect OS
detect_os() {
    OS="$(uname -s)"
    case "$OS" in
        Darwin*)    OS_NAME="macos" ;;
        Linux*)     OS_NAME="linux" ;;
        *)          echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
    esac
}

# Detect architecture
detect_arch() {
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64)     ARCH_NAME="x64" ;;
        amd64)      ARCH_NAME="x64" ;;
        arm64)      ARCH_NAME="arm64" ;;
        aarch64)    ARCH_NAME="arm64" ;;
        *)          echo -e "${RED}Unsupported architecture: $ARCH${NC}"; exit 1 ;;
    esac
}

# Get latest version from GitHub
get_latest_version() {
    if [ "$VERSION" = "latest" ]; then
        VERSION=$(curl -sSL "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
        if [ -z "$VERSION" ]; then
            echo -e "${YELLOW}Could not detect latest version, using v1.0.0${NC}"
            VERSION="v1.0.0"
        fi
    fi
}

# Download and install
download_and_install() {
    DOWNLOAD_URL="https://github.com/$GITHUB_REPO/releases/download/$VERSION/formai-${OS_NAME}-${ARCH_NAME}.tar.gz"

    echo -e "${BLUE}Downloading FormAI $VERSION for $OS_NAME $ARCH_NAME...${NC}"

    # Create temp directory
    TMP_DIR=$(mktemp -d)
    trap "rm -rf $TMP_DIR" EXIT

    # Download
    if ! curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/formai.tar.gz"; then
        echo -e "${RED}Failed to download from: $DOWNLOAD_URL${NC}"
        echo -e "${YELLOW}Release may not exist yet. Please check: https://github.com/$GITHUB_REPO/releases${NC}"
        exit 1
    fi

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    # Extract
    echo -e "${BLUE}Installing to $INSTALL_DIR...${NC}"
    tar -xzf "$TMP_DIR/formai.tar.gz" -C "$INSTALL_DIR"

    # Make executable
    chmod +x "$INSTALL_DIR/formai" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/FormAI" 2>/dev/null || true
}

# Add to PATH
setup_path() {
    # Determine shell config file
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        zsh)    SHELL_RC="$HOME/.zshrc" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                SHELL_RC="$HOME/.bash_profile"
            else
                SHELL_RC="$HOME/.bashrc"
            fi
            ;;
        *)      SHELL_RC="$HOME/.profile" ;;
    esac

    # Check if already in PATH
    if ! grep -q "\.formai" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# FormAI" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.formai:$PATH"' >> "$SHELL_RC"
        echo -e "${GREEN}Added $INSTALL_DIR to PATH in $SHELL_RC${NC}"
    fi

    # Create alias for convenience
    if ! grep -q "alias formai=" "$SHELL_RC" 2>/dev/null; then
        echo 'alias formai="$HOME/.formai/formai"' >> "$SHELL_RC"
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}  ✓ FormAI installed successfully!${NC}"
    echo ""
    echo -e "  ${CYAN}To start FormAI:${NC}"
    echo -e "    ${YELLOW}formai${NC}  (after restarting terminal)"
    echo ""
    echo -e "  ${CYAN}Or run directly:${NC}"
    echo -e "    ${YELLOW}$INSTALL_DIR/formai${NC}"
    echo ""
    echo -e "  ${CYAN}Dashboard:${NC}"
    echo -e "    ${YELLOW}http://localhost:5511${NC}"
    echo ""
}

# Ask to start now
ask_start_now() {
    echo -e "${CYAN}Start FormAI now? [Y/n]${NC} "
    read -r response
    case "$response" in
        [nN][oO]|[nN])
            echo -e "${YELLOW}Run 'formai' to start FormAI later.${NC}"
            ;;
        *)
            echo -e "${GREEN}Starting FormAI...${NC}"
            # Export PATH for current session
            export PATH="$INSTALL_DIR:$PATH"

            # Start server in background
            if [ -f "$INSTALL_DIR/formai" ]; then
                "$INSTALL_DIR/formai" &
            elif [ -f "$INSTALL_DIR/FormAI" ]; then
                "$INSTALL_DIR/FormAI" &
            fi

            # Wait a moment then open browser
            sleep 3

            # Open browser based on OS
            if [ "$OS_NAME" = "macos" ]; then
                open "http://localhost:5511" 2>/dev/null || true
            else
                xdg-open "http://localhost:5511" 2>/dev/null || true
            fi
            ;;
    esac
}

# Main
main() {
    print_banner

    detect_os
    detect_arch
    echo -e "  ${CYAN}Detected:${NC} $OS_NAME $ARCH_NAME"

    get_latest_version
    echo -e "  ${CYAN}Version:${NC} $VERSION"
    echo ""

    download_and_install
    setup_path
    print_success
    ask_start_now
}

main

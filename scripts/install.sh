#!/usr/bin/env bash
# ============================================================================
#  install.sh — bootstrap a fresh Linux server for vpn-servers
# ============================================================================
#
#  Installs:
#    - Docker + Docker Compose plugin
#    - UFW firewall, opens 22/tcp + 443/tcp
#    - Useful tools: jq, qrencode, curl
#
#  Tested on: Ubuntu 22.04, Ubuntu 24.04
#
#  Idempotent: safe to run multiple times.
# ============================================================================

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (use sudo)." >&2
    exit 1
fi

# --- OS detection -----------------------------------------------------------

if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    echo "WARN: this script is tested on Ubuntu. Continue at your own risk."
    read -p "Continue? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# --- System update ----------------------------------------------------------

echo "→ Updating apt..."
apt update -qq
apt upgrade -y -qq

# --- Base tools -------------------------------------------------------------

echo "→ Installing base tools..."
apt install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    jq \
    qrencode \
    ufw \
    git \
    make

# --- Docker -----------------------------------------------------------------

if ! command -v docker &>/dev/null; then
    echo "→ Installing Docker..."

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list

    apt update -qq
    apt install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo "✓ Docker already installed: $(docker --version)"
fi

# --- Firewall ---------------------------------------------------------------

echo "→ Configuring UFW..."

# Don't lock ourselves out: SSH first, then enable.
ufw allow 22/tcp >/dev/null
ufw allow 443/tcp >/dev/null

# --force: skip the "are you sure" prompt
ufw --force enable >/dev/null
echo "✓ UFW: $(ufw status | head -1)"

# --- Done -------------------------------------------------------------------

echo ""
echo "============================================================"
echo "  ✓ Server bootstrap complete"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Edit .env: set SERVER_IP, SNI, etc."
echo "  3. make init       # generate Reality keys"
echo "  4. make up         # start the server"
echo ""

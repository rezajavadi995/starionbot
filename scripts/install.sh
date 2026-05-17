#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rezajavadi995/starionbot.git"
INSTALL_DIR="${HOME}/starionbot"
BIN_DIR="${HOME}/.local/bin"
TARGET_USER="${SUDO_USER:-$USER}"
log() {
  echo -e "\033[1;32m[StarionBot]\033[0m $1"
}

warn() {
  echo -e "\033[1;33m[Warning]\033[0m $1"
}

error() {
  echo -e "\033[1;31m[Error]\033[0m $1"
}

log "Starting installation..."


if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update

  sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    openssl \
    curl \
    ufw \
    dnsutils \
    net-tools

  if ! command -v docker >/dev/null 2>&1; then
    log "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sudo sh
  else
    log "Docker already installed."
  fi

  TARGET_USER="${SUDO_USER:-$USER}"
  sudo usermod -aG docker "$TARGET_USER" || true

  if ! docker compose version >/dev/null 2>&1; then
    warn "Docker Compose not found."
    sudo apt-get install -y docker-compose-plugin || true
  else
    log "Docker Compose already installed."
  fi
fi


if [ ! -d "$INSTALL_DIR/.git" ]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  git -C "$INSTALL_DIR" pull --ff-only
fi

cd "$INSTALL_DIR"

if [ ! -d ".venv" ]; then
  log "Creating virtual environment..."
  python3 -m venv .venv
fi

. .venv/bin/activate

pip install --upgrade pip

pip install -e . || {
  error "Failed to install Python package."
  exit 1
}

mkdir -p "$BIN_DIR"
ln -sfn "$INSTALL_DIR/.venv/bin/tgbot" "$BIN_DIR/tgbot"
ln -sfn "$INSTALL_DIR/.venv/bin/gtbot" "$BIN_DIR/gtbot"
if ! grep -q '.local/bin' "$HOME/.bashrc"; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi
export PATH="$HOME/.local/bin:$PATH"

cat <<MSG

✅ StarionBot installation complete.


Next steps:
1) cp .env.example .env
2) run gtbot and complete Domain/SSL/Nginx/Webhook setup
3) docker compose up -d --build

To open management menu, run:
  gtbot
  # or tgbot --help

If command not found, add this to your shell profile:
  export PATH=\"\$HOME/.local/bin:\$PATH\"
MSG

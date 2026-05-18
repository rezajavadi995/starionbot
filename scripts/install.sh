#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rezajavadi995/starionbot.git"
INSTALL_DIR="${HOME}/starionbot"
BIN_DIR="/usr/local/bin"
TARGET_USER="${SUDO_USER:-$USER}"
log() {
  echo -e "\033[1;32m[StarionBot]\033[0m $1"
}

ensure_apt_package() {
  local package="$1"
  if dpkg -s "$package" >/dev/null 2>&1; then
    return 0
  fi
  sudo apt-get install -y "$package"
}

docker_ready() {
  command -v docker >/dev/null 2>&1 && sudo systemctl is-active --quiet docker
}

install_docker_ce() {
  if docker_ready; then
    return 0
  fi

  sudo apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc || true

  ensure_apt_package ca-certificates
  ensure_apt_package curl
  ensure_apt_package gnupg
  ensure_apt_package lsb-release

  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /tmp/docker.gpg
    sudo mv /tmp/docker.gpg /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local arch codename
  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME}")"
  echo \
    "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
}

ensure_apt_package() {
  local package="$1"
  if dpkg -s "$package" >/dev/null 2>&1; then
    return 0
  fi
  sudo apt-get install -y "$package"
}

docker_ready() {
  command -v docker >/dev/null 2>&1 && sudo systemctl is-active --quiet docker
}

install_docker_ce() {
  if docker_ready; then
    return 0
  fi

  sudo apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc || true

  ensure_apt_package ca-certificates
  ensure_apt_package curl
  ensure_apt_package gnupg
  ensure_apt_package lsb-release

  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /tmp/docker.gpg
    sudo mv /tmp/docker.gpg /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local arch codename
  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME}")"
  echo \
    "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
}

ensure_apt_package() {
  local package="$1"
  if dpkg -s "$package" >/dev/null 2>&1; then
    return 0
  fi
  sudo apt-get install -y "$package"
}

docker_ready() {
  command -v docker >/dev/null 2>&1 && sudo systemctl is-active --quiet docker
}

install_docker_ce() {
  if docker_ready; then
    return 0
  fi

  sudo apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc || true

  ensure_apt_package ca-certificates
  ensure_apt_package curl
  ensure_apt_package gnupg
  ensure_apt_package lsb-release

  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /tmp/docker.gpg
    sudo mv /tmp/docker.gpg /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local arch codename
  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME}")"
  echo \
    "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
}

ensure_apt_package() {
  local package="$1"
  if dpkg -s "$package" >/dev/null 2>&1; then
    return 0
  fi
  sudo apt-get install -y "$package"
}

docker_ready() {
  command -v docker >/dev/null 2>&1 && sudo systemctl is-active --quiet docker
}

install_docker_ce() {
  if docker_ready; then
    return 0
  fi

  sudo apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc || true

  ensure_apt_package ca-certificates
  ensure_apt_package curl
  ensure_apt_package gnupg
  ensure_apt_package lsb-release

  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /tmp/docker.gpg
    sudo mv /tmp/docker.gpg /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local arch codename
  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME}")"
  echo \
    "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
}

ensure_apt_package() {
  local package="$1"
  if dpkg -s "$package" >/dev/null 2>&1; then
    return 0
  fi
  sudo apt-get install -y "$package"
}

docker_ready() {
  command -v docker >/dev/null 2>&1 && sudo systemctl is-active --quiet docker
}

install_docker_ce() {
  if docker_ready; then
    return 0
  fi

  sudo apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc || true

  ensure_apt_package ca-certificates
  ensure_apt_package curl
  ensure_apt_package gnupg
  ensure_apt_package lsb-release

  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /tmp/docker.gpg
    sudo mv /tmp/docker.gpg /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local arch codename
  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME}")"
  echo \
    "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
}

printf "\n[StarionBot] Starting installation...\n"
command -v git >/dev/null || { echo "git is required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  ensure_apt_package nginx
  ensure_apt_package certbot
  ensure_apt_package python3-certbot-nginx
  ensure_apt_package openssl
  ensure_apt_package curl
  ensure_apt_package ufw
  ensure_apt_package dnsutils
  ensure_apt_package net-tools
  install_docker_ce
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
pip install -e .

mkdir -p "$BIN_DIR"
ln -sfn "$INSTALL_DIR/.venv/bin/tgbot" "$BIN_DIR/tgbot"
ln -sfn "$INSTALL_DIR/.venv/bin/gtbot" "$BIN_DIR/gtbot"


pip install --upgrade pip

cat <<'MSG'
✅️
Next steps:
1) gtbot
2) tgbot --help

The setup wizard will guide first-run configuration interactively.
No manual .env copy is required.

MSG
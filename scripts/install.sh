#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rezajavadi995/starionbot.git"
INSTALL_DIR="${HOME}/starionbot"
BIN_DIR="${HOME}/.local/bin"

printf "\n[StarionBot] Starting installation...\n"
command -v git >/dev/null || { echo "git is required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

if [ ! -d "$INSTALL_DIR/.git" ]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  git -C "$INSTALL_DIR" pull --ff-only
fi

cd "$INSTALL_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .

mkdir -p "$BIN_DIR"
ln -sfn "$INSTALL_DIR/.venv/bin/tgbot" "$BIN_DIR/tgbot"

cat <<MSG

✅ StarionBot installation complete.

Next steps:
1) cp .env.example .env
2) edit .env with your real credentials
3) docker compose up -d --build

To open management menu, run:
  tgbot --help

If command not found, add this to your shell profile:
  export PATH=\"\$HOME/.local/bin:\$PATH\"
MSG

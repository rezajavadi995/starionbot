# StarionBot

StarionBot is a Telegram Bot and Telegram Mini App platform for a Crash game powered by Telegram Stars and TON.

## Current Stage
Phase 3 is in progress. The repository now includes real backend health checks, a transactional wallet ledger core, mandatory join flow handlers, and bilingual message architecture.

## Table of Contents
- [Core Features](#core-features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Local Development](#local-development)
- [One-Line Installer](#one-line-installer)
- [Management CLI](#management-cli)
- [Environment Variables](#environment-variables)
- [Security Baseline](#security-baseline)

## Core Features
- FastAPI API service with live health report
- aiogram bot application structure with mandatory join verification flow
- SQLAlchemy async models for users, wallets, and ledger transactions
- Idempotent atomic ledger transaction service
- Alembic migration baseline
- Crash engine scaffold and websocket route
- Docker Compose stack with Postgres and Redis
- Pre-commit, lint, format, type-check, and secret scanning setup

## Architecture
```text
bot/
  api/              FastAPI routes
  botapp/           aiogram dispatchers and handlers
  core/             settings and logging
  db/               SQLAlchemy engine/session/base
  models/           ORM entities
  services/         health and ledger services
  i18n/             language messages

games/
  crash/            crash engine

ui/
  src/components/   mini app components

scripts/
  install.sh        installer script
```

## Requirements
- Python 3.12+
- Docker and Docker Compose
- Git

## Local Development
```bash
git clone https://github.com/rezajavadi995/starionbot.git
cd starionbot
cp .env.example .env
# Fill .env with real credentials

docker compose up --build
```

Health endpoint:
```bash
curl http://localhost:8000/health
```

## One-Line Installer
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/rezajavadi995/starionbot/main/scripts/install.sh)
```

The installer:
- clones or updates the repository in `~/starionbot`
- creates `.venv` and installs dependencies
- creates a symlink at `~/.local/bin/tgbot`

## Management CLI
After installation:
```bash
tgbot --help
```

Useful commands:
```bash
tgbot health
tgbot add-admin 123456789
```

If `tgbot` is not found, add this to your shell profile:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Environment Variables
Use `.env.example` as the source of truth. Never commit real secrets.

Required keys include:
- `TELEGRAM_BOT_TOKEN`
- `POSTGRESQL_URL`
- `REDIS_URL`
- `WEBHOOK_SECRET`
- `MANDATORY_JOIN_CHANNEL`
- `ADMIN_IDS`
- `TON_API_KEY`
- `TON_WALLET_MNEMONIC`

## Security Baseline
- No hardcoded secrets
- `.env` is ignored by git
- structured logging with sensitive-field masking
- pre-commit hooks with Gitleaks and TruffleHog
- idempotency keys on ledger transactions
- row locking for wallet updates

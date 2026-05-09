# StarionBot

StarionBot یک پلتفرم Telegram Bot + Telegram Mini App برای Crash Game است که با **Telegram Stars** و **TON** کار می‌کند.

> وضعیت فعلی: فاز 2 (زیرساخت دیتابیس، تراکنش اتمیک، installer، امنیت پایه، UI scaffold)

---

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quick Start (Dev)](#quick-start-dev)
- [One-line Installer](#one-line-installer)
- [CLI Management](#cli-management)
- [Security](#security)
- [Developer Tooling](#developer-tooling)

---

## Features
- FastAPI backend + aiogram-ready structure
- Crash engine (isolated core) + websocket scaffold
- PostgreSQL / Redis with Docker Compose health checks
- Atomic ledger service with idempotency key support
- Secret-safe config with `.env` + `pydantic-settings`
- Secret scanning with **Gitleaks** + **TruffleHog**
- Starter Telegram Mini App Crash UI components

## Architecture
```text
bot/                FastAPI app, config, db, services
games/              game engines (Crash)
ui/                 Telegram Mini App (React/TS)
admin_tools/        Typer + Rich terminal management
payment-engine/     reserved internal module
wallet-core/        reserved internal module
fraud-detection/    reserved internal module
deployment/         ops and infrastructure scripts
```

## Requirements
- Python 3.12+
- Docker + Docker Compose
- Git

## Quick Start (Dev)
```bash
git clone https://github.com/rezajavadi995/starionbot.git
cd starionbot
cp .env.example .env
# مقادیر واقعی را در .env قرار دهید

docker compose up --build
```

Health check:
```bash
curl http://localhost:8000/health
```

## One-line Installer
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/rezajavadi995/starionbot/main/scripts/install.sh)
```

Installer after completion:
- یک symlink برای `tgbot` داخل `~/.local/bin/tgbot` می‌سازد.
- مسیر پروژه را در `~/starionbot` آماده می‌کند.
- virtualenv را می‌سازد و dependencyها را نصب می‌کند.

## CLI Management
بعد از نصب، فقط بزن:
```bash
tgbot --help
```

با همین دستور منوی مدیریتی/دستورات CLI قابل مشاهده است.

نمونه:
```bash
tgbot health
tgbot add-admin 123456789
```

## Security
- هیچ secretی داخل کد hardcode نمی‌شود.
- `.env` داخل git نادیده گرفته می‌شود.
- startup config validation فعال است.
- mask کردن لاگ‌های حساس انجام می‌شود.
- pre-commit برای کشف secret leak فعال است.

## Developer Tooling
- Ruff
- Black
- Mypy
- Pytest
- pre-commit

---

اگر می‌خواهی از همینجا فاز بعدی (bot flows + payments + realtime round loop) را کامل کنیم، مستقیم از issue/PR لیست feature بده تا مرحله‌ای جلو برویم.

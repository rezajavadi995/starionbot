# StarionBot

پلتفرم Telegram Bot + Mini App برای Crash Game با Telegram Stars و TON.

## Quick Start

### 1) Environment
```bash
cp .env.example .env
```

### 2) Run with Docker
```bash
docker compose up --build
```

### 3) Health check
```bash
curl http://localhost:8000/health
```

## One-line installer (placeholder)
```bash
bash <(curl -fsSL https://example.com/starionbot/install.sh)
```

## Security model
- No secrets in code; all sensitive values come from `.env`.
- `.env` is ignored by git.
- Startup validation with `pydantic-settings`.
- Structured logging with masking for sensitive fields.
- Pre-commit secret scanning with Gitleaks and TruffleHog.

## Architecture
- `bot/`: FastAPI + aiogram app services.
- `games/`: isolated game engines (Crash now, more later).
- `ui/`: Telegram Mini App (React + TypeScript).
- `api-client/`: generated clients and contracts.
- `docs/`: architecture & operations docs.
- Reserved private/internal modules:
  - `payment-engine/`
  - `wallet-core/`
  - `fraud-detection/`
  - `admin-tools/`
  - `deployment/`

## CLI
```bash
tgbot health
```

## CI/CD baseline
GitHub Actions workflow runs lint and tests on push/PR.

# StarionBot Prompt Audit and Execution Roadmap

This document records the implementation status of the supplied Codex prompts and turns the
remaining work into concrete delivery phases. It is intentionally explicit so future agents can
continue from the repository state without relying on unavailable prior chat history.

## Audit scope

Sources checked in this repository:

- `README.md`
- `docs/project-phases.md`
- `.env.example`
- `.gitignore`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `scripts/install.sh`
- `admin_tools/cli.py`
- `admin_tools/prod_setup.py`
- `bot/`
- `games/`
- `ui/src/components/crash/`
- `tests/`

## Prompt 1 — Full StarionBot platform

### Implemented

#### Repository safety and secret hygiene

- `.env` is ignored by git.
- `.env.example` exists and includes non-secret placeholders.
- `pydantic-settings` and `python-dotenv` are project dependencies.
- Pre-commit hooks include Ruff, Black, Gitleaks, and TruffleHog.
- GitHub Actions runs Ruff, Black, and Mypy.
- Structured logging exists with sensitive-key masking.

#### Backend foundation

- FastAPI application exists.
- aiogram 3 application structure exists.
- PostgreSQL async URL configuration exists.
- Redis URL configuration exists.
- SQLAlchemy async session and model baseline exists.
- Alembic migration baseline exists.
- Dockerfile and Docker Compose exist.
- Health endpoint exists.

#### Crash backend foundation

- Isolated crash engine exists under `games/crash/`.
- Realtime crash runtime exists.
- WebSocket broadcast route exists.
- Persistent crash round and bet models exist.
- Bet placement uses idempotency keys.
- Cashout uses idempotency keys and row-level bet locking.
- Loss finalization exists.
- Wallet ledger core exists and is transaction-oriented.
- Crash audit logging exists.
- Financial reconciliation and crosscheck services exist.

#### Telegram Stars foundation

- Stars invoice payload builder exists.
- Successful Stars payment parser exists.
- Idempotent successful-payment application exists.
- User Stars balance table exists.

#### Referral foundation

- User model supports `referred_by_user_id`.
- Referral payout journal exists.
- Referral commission hook exists for house-profit based payouts.

#### i18n and mandatory join foundation

- Persian and English message architecture exists.
- Mandatory join handlers exist.

#### Admin and CLI foundation

- `tgbot` and `gtbot` entrypoints are registered.
- Rich/Typer management CLI exists.
- CLI includes Redis, PostgreSQL, TON, bot token, mandatory join, health, migrations,
  Docker, Stars, reconciliation, Phase 4 check, production HTTPS, and webhook menus.

#### Frontend crash component scaffold

- `ui/src/components/crash/CrashArena.tsx`
- `ui/src/components/crash/MultiplierDisplay.tsx`
- `ui/src/components/crash/CrashGraph.tsx`
- `ui/src/components/crash/BettingPanel.tsx`
- `ui/src/components/crash/RoundHistory.tsx`
- `ui/src/components/crash/LivePlayers.tsx`
- `ui/src/components/crash/RewardOverlay.tsx`
- `ui/src/components/crash/BottomNavbar.tsx`

### Partially implemented

#### Production-ready deployment

- One-line installer exists and installs core production packages on apt-based systems.
- Domain, SSL, Nginx, webhook, Mini App URL, and HTTPS validation CLI flows exist.
- More production hardening is still needed for systemd units, service restarts, backups,
  full webhook endpoint handling, frontend build/deployment, and non-Debian systems.

#### Telegram Stars production payment flow

- Backend primitives exist, but the bot-side real Telegram invoice sending and complete
  cancel/rollback UX still need end-to-end integration tests and production wiring.

#### TON Connect

- TON credentials can be configured.
- A placeholder TON Connect config endpoint exists.
- Real TON Connect SDK integration, wallet session persistence, transaction signing,
  verification, and status handling are still missing.

#### Mini App UI

- Crash UI component files exist.
- A full production React/Tailwind/Framer Motion project shell, build pipeline, SDK wiring,
  websocket state manager, and real API client integration still need completion.

#### Admin panel

- Terminal admin tooling exists.
- Telegram reply-keyboard admin panel is not complete.

#### Anti-abuse and security controls

- Transaction idempotency and row locking exist in the wallet/crash core.
- Full rate limiting, anti-spam, fraud scoring, CSRF/JWT architecture, websocket auth,
  and optimistic locking coverage remain future work.

### Missing or not production-complete

- Real deposit and withdrawal queue systems for Stars and TON.
- Admin approval workflow for withdrawals.
- User profile page with Telegram photo, stats, balances, referral stats, and game stats.
- Referral leaderboard and anti-abuse analytics.
- Replay system and provably-fair public verification flow.
- Sound system integration.
- Rotating file logs.
- GitHub update workflow in CLI.
- Systemd service creation and controls.
- Database backup/restore tools.
- Full README screenshots.

## Prompt 2 — Quality gates

### Implemented now

The following checks pass in the current repository state:

- `ruff check .`
- `black --check .`
- `mypy bot games admin_tools`
- `pytest -q`

### Ongoing rule

Every future implementation phase must run those checks before commit. If a check cannot run due to
a real environment limitation, the limitation must be documented in the final report.

## Prompt 3 — Production deployment extension

### Implemented

#### Installer

`scripts/install.sh` now installs these production dependencies on apt-based hosts:

- `nginx`
- `certbot`
- `python3-certbot-nginx`
- `docker.io`
- `docker-compose-plugin`
- `openssl`
- `curl`
- `ufw`
- `dnsutils`
- `net-tools`

It also creates both `tgbot` and `gtbot` symlinks.

#### CLI menu

The interactive menu includes:

- Configure Domain & SSL
- Configure Nginx Reverse Proxy
- Configure Telegram Webhook URL
- Configure Telegram Mini App
- Validate HTTPS Infrastructure

#### Domain and SSL flow

The production setup module supports:

- Primary domain validation.
- Dynamic subdomain expansion.
- DNS resolution checks.
- Public server IP match checks.
- Cloudflare proxy warning.
- Certbot standalone certificate issuance.
- Certbot auto-renewal enablement.
- Certbot dry-run renewal validation.
- Certificate validity check.
- `.env` persistence for domain, webhook, Mini App, and SSL paths.

#### Nginx flow

The production setup module generates a StarionBot Nginx site with:

- HTTP to HTTPS redirect.
- HTTP/2 TLS listeners.
- Frontend reverse proxy to `127.0.0.1:3000`.
- Backend/API reverse proxy to `127.0.0.1:8000`.
- WebSocket upgrade headers.
- Gzip.
- Security headers.

#### Telegram webhook flow

The production setup module:

- Reads `TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET`, and `WEBHOOK_URL` from `.env`.
- Calls Telegram `setWebhook` without exposing the token in a shell command.
- Verifies `getWebhookInfo` returns the configured URL.

#### HTTPS validation menu

The validation flow reports:

- DNS app status.
- DNS API status.
- Port 80 status.
- Port 443 status.
- Nginx status.
- SSL certificate status.
- HTTP to HTTPS redirect status.
- Mini App reachability.
- Webhook reachability.
- Backend health endpoint availability.

### Still pending for production completeness

- Actual `/webhook` FastAPI route for Telegram updates if webhook mode is selected.
- Systemd unit generation for API, bot worker, and optional frontend service.
- Service start/stop/restart/status controls.
- GitHub update command that pulls, installs dependencies, runs migrations, and restarts services.
- Database backup/restore.
- Frontend build artifact deployment behind Nginx.
- Runtime smoke test that validates WebSocket connectivity through Nginx.

## Execution roadmap from this point

### Phase 4A — Close backend Crash settlement

Goal: make the backend Crash loop financially closed and auditable.

Tasks:

1. ✅ Persist a financial snapshot automatically after each crashed round.
2. Ensure `tgbot phase4-check --strict` can verify DB, Redis, websocket runtime, migrations,
   reconciliation, and referral payout journal readiness.
3. ✅ Add tests for automatic round financial persistence.
4. ✅ Fix known audit-log consistency issues, including cashout audit records using the real runtime
   round id.
5. Update Phase 4 docs only after checks pass.

Exit criteria:

- `ruff check .` passes.
- `black --check .` passes.
- `mypy bot games admin_tools` passes.
- `pytest -q` passes.
- `tgbot phase4-check --strict` passes in an environment with DB/Redis configured.

### Phase 4B — Production operations hardening

Goal: make `gtbot` able to operate a real deployed host.

Tasks:

1. Add systemd unit generation for API and bot process.
2. Add systemd controls in CLI.
3. Add GitHub update workflow in CLI.
4. Add database backup/restore tools.
5. Add Nginx/WebSocket smoke validation.
6. Add documentation for safe production deployment and rollback.

### Phase 5 — Mini App Crash UI production wiring

Goal: turn the existing crash UI component scaffold into a working Telegram Mini App.

Tasks:

1. Add or complete React/TypeScript project configuration.
2. Add TailwindCSS and theme variables.
3. Add Telegram Mini App SDK wiring.
4. Add websocket state manager and reusable crash hooks.
5. Wire betting, cashout, history, live players, balances, and reward overlay to APIs.
6. Add mobile-first performance optimizations.

### Phase 6 — Payments and wallet integration

Goal: make Stars and TON flows real and production-safe.

Tasks:

1. Send real Telegram Stars invoices from bot handlers.
2. Handle successful, canceled, duplicate, and replayed payment states.
3. Add TON Connect frontend SDK integration.
4. Persist TON wallet sessions.
5. Implement transaction signing, verification, and status handling.
6. Add withdrawal queue architecture for Stars and TON.

### Phase 7 — User, referral, and admin platform

Goal: complete platform-level product systems.

Tasks:

1. Profile page and APIs.
2. Referral stats and leaderboard.
3. Anti-self-referral and abuse checks.
4. Telegram reply-keyboard admin panel.
5. Admin statistics and audit views.

### Phase 8 — Security, observability, and release readiness

Goal: make the public repository and deployed system production resilient.

Tasks:

1. Add rate limiting and anti-spam middleware.
2. Add websocket auth/validation strategy.
3. Add rotating logs and deployment log paths.
4. Add full CI pytest execution.
5. Add secret scanning CI jobs.
6. Add runbooks and incident rollback docs.

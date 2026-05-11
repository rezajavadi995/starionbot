# StarionBot Project Phases

## Current status
Phase 4A backend Crash settlement closure is the active workstream. The repository already has
Phase 4 groundwork plus production deployment CLI scaffolding, but the official stop-point is not
closed until strict verification passes in a clean DB/Redis environment.

For the detailed prompt-by-prompt implementation audit, see
[`docs/prompt-audit-and-roadmap.md`](prompt-audit-and-roadmap.md).

## Completed baseline (Phases 1-3)
- Core backend service skeleton (FastAPI, aiogram structure)
- Health check service
- Transactional ledger core
- Mandatory join flow foundation
- Bilingual i18n baseline
- Docker Compose baseline with Postgres/Redis
- Pre-commit + lint/format/type/security hooks

## Active and next phases

### Phase 4A — Crash Game Settlement Closure (Backend-first)
- ✅ Isolated crash engine round lifecycle (runtime loop added)
- ✅ WebSocket round state broadcast and subscriptions (shared runtime)
- ✅ Persistent round and bet history models + migrations (baseline schema)
- ✅ Bet and cashout idempotency keys
- ✅ Reconciliation and financial crosscheck services
- ✅ Referral payout journal baseline
- ✅ Cashout audit records consistently use the real runtime round id
- ✅ Automatic persisted financial snapshot after every completed round
- Strict phase verification against a configured DB/Redis environment

#### Phase 4A exit criteria
- `tgbot phase4-check --strict` passes in a clean environment with DB/Redis configured
- Reconciliation snapshot exists for recent rounds (`crash_round_financials`)
- Crosscheck report returns zero mismatches for stable rounds
- Referral payout journal entries are generated for eligible losing bets
- `ruff check .`, `black --check .`, `mypy bot games admin_tools`, and `pytest -q` pass

### Phase 4B — Production Operations Hardening
- ✅ Production package installation added to installer for apt-based hosts
- ✅ Domain/SSL/Nginx/Webhook/Mini App/HTTPS validation menu entries exist
- ✅ Dynamic certbot domain flow and Nginx reverse proxy config exist
- Systemd unit generation for API/bot/frontend services
- Systemd controls from CLI
- GitHub update workflow from CLI
- Database backup/restore tools
- WebSocket smoke validation through Nginx

### Phase 5 — Mini App Crash UI (Production UX)
- Crash screen components (multiplier, graph, betting panel, history, live players)
- FPS-safe animation controller and optimized rendering
- Mobile-first dark/neon design system
- State synchronization with WebSocket manager hooks
- Telegram Mini App SDK integration
- TailwindCSS/Framer Motion project wiring

### Phase 6 — Payments and Wallet Integrations
- Telegram Stars top-up flow + duplicate protection
- TON Connect wallet connect/disconnect/sign/verify
- Deposit/withdrawal queue architecture and verification pipeline
- Withdrawal admin approval and fraud-review readiness

### Phase 7 — Platform Systems
- Referral tracking and anti-abuse rules
- Profile stats aggregation
- Admin panel expansion (join channel, admins, health, stats)
- Audit logs and risk/fraud signals
- Referral leaderboard readiness

### Phase 8 — Ops, Security, and Release Hardening
- Installer hardening + systemd automation
- CI quality gates (ruff/black/mypy/pytest/security)
- Staging/production configuration separation
- Observability and runbook docs
- Rate limiting, anti-spam, websocket validation, and deployment rollback docs

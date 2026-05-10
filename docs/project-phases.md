# StarionBot Project Phases

## Current status
Phase 4 backend groundwork is currently active based on the README status.

## Completed baseline (Phases 1-3)
- Core backend service skeleton (FastAPI, aiogram structure)
- Health check service
- Transactional ledger core
- Mandatory join flow foundation
- Bilingual i18n baseline
- Docker Compose baseline with Postgres/Redis
- Pre-commit + lint/format/type/security hooks

## Next main phases

### Phase 4 — Crash Game Realtime Loop (Backend-first)
- ✅ Isolated crash engine round lifecycle (runtime loop added)
- ✅ WebSocket round state broadcast and subscriptions (shared runtime)
- Cashout validation window and round locking
- ✅ Persistent round and bet history models + migrations (baseline schema)
- Transaction-safe win/loss settlement with idempotency keys

#### Phase 4 exit criteria (stop-point readiness)
- `tgbot phase4-check` passes in a clean environment
- Reconciliation snapshot exists for recent rounds (`crash_round_financials`)
- Crosscheck report returns zero mismatches for stable rounds
- Referral payout journal entries are generated for eligible losing bets

### Phase 5 — Mini App Crash UI (Production UX)
- Crash screen components (multiplier, graph, betting panel, history, live players)
- FPS-safe animation controller and optimized rendering
- Mobile-first dark/neon design system
- State synchronization with WebSocket manager hooks

### Phase 6 — Payments and Wallet Integrations
- Telegram Stars top-up flow + duplicate protection
- TON Connect wallet connect/disconnect/sign/verify
- Deposit/withdrawal queue architecture and verification pipeline

### Phase 7 — Platform Systems
- Referral tracking and anti-abuse rules
- Profile stats aggregation
- Admin panel expansion (join channel, admins, health, stats)
- Audit logs and risk/fraud signals

### Phase 8 — Ops Hardening
- Installer hardening + systemd automation
- CI quality gates (ruff/black/mypy/pytest/security)
- Staging/production configuration separation
- Observability and runbook docs

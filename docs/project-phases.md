# StarionBot Project Roadmap

## Current phase window (as of May 16, 2026)
- **Phase 4A — Crash settlement closure:** in progress
- **Phase 4B — Production operations hardening:** in progress

## Phase 4A checklist
- [x] Runtime crash loop with websocket fan-out
- [x] Crash rounds/bets persistence + migrations
- [x] Reconciliation commands (`reconcile-round`, `reconcile-recent`, `reconcile-verify`)
- [x] Basic Stars invoice/payment flow
- [ ] Strict stop-point verification in clean production-like env (`phase4-check --strict`)
- [ ] End-to-end payment webhook ingestion hardening audit

## Phase 4B checklist
- [x] Domain + SSL setup flow in `gtbot`
- [x] Nginx reverse proxy generation with HTTP->HTTPS redirect and websocket headers
- [x] Telegram webhook setup/verification menu action
- [x] Mini App URL setup and HTTPS reachability check
- [x] HTTPS infrastructure validation menu
- [x] Systemd service templates + install wiring
- [x] Backup/restore operational runbook
- [x] Websocket smoke-check command in CLI

## Next phases
### Phase 5 — Mini App and gameplay UX
- Multiplayer crash UX polish, reconnect behavior, resilient websocket client fallback.

### Phase 6 — Payments and treasury
- Stars ingestion hardening, TON deposit pipeline, immutable payment audit reporting.

### Phase 7 — Platform systems
- Referral anti-abuse, profile and analytics aggregation, expanded admin observability.

### Phase 8 — Reliability and release engineering
- Full staging/prod parity, incident runbooks, and automated rollback-safe deploy flow.

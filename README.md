# personal-agent

Personal assistant on Hermes Agent via Telegram. Milestone 1 (platform skeleton): isolated networks, per-zone egress proxies, control bot, host timers, deploy tooling.

- `make test` - unit tests for the control bot
- `make preflight` - read-only VPS checks
- `make deploy` - sync and start (needs approval; see `docs/RUNBOOK.md`)

Docs: `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/RUNBOOK.md`.

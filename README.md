# personal-agent

The owner's personal finance assistant on Hermes Agent through Telegram, on one VPS and deployed from this repo: a vault bot for the money, a front bot for general questions and the web, a control bot for approvals (no LLM), isolated networks with per-zone egress proxies, and host timers for statements and backups. A comms zone is built and not started.

- `make venv`, once, then `make test` - every test in the repo
- `make preflight` - read-only VPS checks
- `make deploy` - sync and start (needs the owner's OK; see `docs/RUNBOOK.md`)
- `make verify` - is the bot up as the recipe says (read-only)
- `make mirror` - refresh the full copy of the VPS data and secrets in the git-ignored `private/`

Moving to another VPS, with nothing to tune again: `docs/REBUILD.md`.

Docs: `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/RUNBOOK.md`, `docs/LAPTOP.md`; state and decisions in `docs/PROGRESS.md`.

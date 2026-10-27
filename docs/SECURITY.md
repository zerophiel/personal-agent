# Security (M1)

Invariants are enforced in infrastructure, not prompts.
- Egress: internal-only networks + per-zone Squid default-deny allowlists (`config/squid/`).
- Telegram: control checks `from.id == MY_TELEGRAM_ID` and `chat.type == private` on every message and callback; others dropped and logged (`services/control/control.py`, tested).
- Containers: `cap_drop: ALL`, `no-new-privileges`, read-only root fs where possible, memory/CPU caps, `oom_score_adj` per brief.
- Secrets: root-only dir `/opt/personal-agent-secrets` (0700), injected as Docker secrets; plaintext never in the repo (`.gitignore`). sops+age is added in M2 when zone secrets multiply.
- Maintenance never deletes volumes (`scripts/prune.sh`).
- Known limits: DNS still resolves inside internal networks; Hermes read-only config mount is unverified (spike in M1/M2).

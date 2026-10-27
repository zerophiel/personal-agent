# Runbook (M1)

## First-time VPS setup (each step needs owner approval)
1. `make preflight` - read-only: must show KVM (not openvz/lxc), Ubuntu 24.04, enough disk.
2. Harden SSH (keys only, no root login), ufw default-deny inbound except 22, unattended-upgrades, Docker from Docker's apt repo, 4 GB swap, journald + Docker log caps.
3. Create bots in BotFather. Usernames must end in `bot`. Disable "Allow Groups" for each.
4. `make secret-set NAME=telegram_control_token` (prompted on the VPS, never in chat).
5. R2 backup: create `/opt/personal-agent-secrets/restic.env` on the VPS (see `scripts/backup.sh`).
6. `make deploy`, then `make status`.

## Host state (done 2026-10-27)
KVM, Ubuntu 24.04.4, sshd drop-in `/etc/ssh/sshd_config.d/00-hardening.conf` (no root, no password), ufw deny-in/allow 22, unattended-upgrades, Docker 29.9.2 + Compose v5.6.1 from Docker apt repo, daemon log rotation 10m x3, journald 500M cap, swap ~6 GB, TZ Asia/Jakarta. `ubuntu` is NOT in the docker group; use `sudo docker`.

## Gate checks for M1
- Blocked-domain egress test: from the control container, `https://example.com` via squid-ctl must return 403.
- `make prune-dry` keeps images of the current compose and `releases/previous.txt`; no volume is touched.
- Restore test: `restic restore latest --target /tmp/restore-test` then inspect.

## Restore
Always restore to a scratch directory, verify the ledger, then copy deliberately.

## Secrets rotation
Telegram: BotFather `/revoke`, then `make secret-set`.

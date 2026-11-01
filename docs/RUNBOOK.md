# Runbook (M1)

## First-time VPS setup (each step needs owner approval)
1. `make preflight` - read-only: must show KVM (not openvz/lxc), Ubuntu 24.04, enough disk.
2. Harden SSH (keys only, no root login), ufw default-deny inbound except 22, unattended-upgrades, Docker from Docker's apt repo, 4 GB swap, journald + Docker log caps.
3. Create bots in BotFather. Usernames must end in `bot`. Disable "Allow Groups" for each (Bot Settings -> Allow Groups
   -> off). On 2026-11-01 getMe showed it still on for `@danoevault_agent` and `@danoecontrol_bot`; the Hermes configs
   drop groups (`allowed_chats: "none"`) and control drops them in code, so this closes it at Telegram as well.
4. `make secret-set NAME=telegram_control_token` (prompted on the VPS, never in chat).
5. R2 backup: create `/opt/personal-agent-secrets/restic.env` on the VPS (see `scripts/backup.sh`).
6. `make deploy`, then `make status`.

## Host state (done 2026-10-27)
KVM, Ubuntu 24.04.4, sshd drop-in `/etc/ssh/sshd_config.d/00-hardening.conf` (no root, no password), ufw deny-in/allow 22, unattended-upgrades, Docker 29.9.2 + Compose v5.6.1 from Docker apt repo, daemon log rotation 10m x3, journald 500M cap, swap ~6 GB, TZ Asia/Jakarta. `ubuntu` is NOT in the docker group; use `sudo docker`.

## Gate checks for M1
- Blocked-domain egress test: from the control container, `https://example.com` via squid-ctl must return 403.
- `make prune-dry` keeps images of the current compose and `releases/previous.txt`; no volume is touched.
- Restore test: `restic restore latest --target /tmp/restore-test` then inspect.

## Control bot (M3, live since 2026-11-01)
- `@danoecontrol_bot`, owner only: `/status` (waiting, approved, rejected, invalid counts), `/usulan` (posts the waiting
  proposals again with their buttons), `/ping`. A proposal card shows the agent's summary, permission change, files,
  risk and rollback; Setujui/Tolak work once. Approved means recorded in `control-state/approved/`, not applied: the
  applier is not built yet (contract in `docs/SECURITY.md`).
- Folders: `sudo bash scripts/data-dirs.sh` (also run by `make deploy`) before the first start.
- Deploy only control: rsync as `make deploy` does, then
  `sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env up -d --build --wait control`.
- Read its state without printing nonces: `sudo docker exec -i personal-agent-control-1 python -I -` with a short
  read-only script on `file:/state/control.db?mode=ro` (counts and statuses only).

## Front zone (M3, live since 2026-11-01 11:34 WIB)
`@danoefront_agent`: Hermes on Haiku 5.5 with web search, memory (each write needs the owner's OK) and one MCP tool,
`submit` (change-proposals), which sends a change request to the control bot. No shell, code, files, browser or skills.
It starts only with `--profile front`; `make deploy` never starts or stops it. First start, in order (steps 2-5 done
on 1 Nov; 1 and 6 are the owner's):
1. BotFather: `@danoefront_agent` -> Bot Settings -> Allow Groups -> off.
2. Anthropic Console: a separate workspace for front with a USD 40 monthly limit, and an API key from that workspace
   (with the vault's key front would spend the finance bot's budget; `render-front-env.sh` refuses the vault key).
3. `make secret-set NAME=telegram_front_token` and `make secret-set NAME=anthropic_front_key` (prompted on the VPS).
4. On the VPS: `sudo bash scripts/data-dirs.sh` (done 2026-11-01), then `sudo bash scripts/render-front-env.sh`.
   The `cardblock` plugin (built 2026-11-01) drops any message holding a card-like number before the model sees it,
   deletes it in Telegram and tells the owner (`docs/SECURITY.md`, front zone).
5. Start: `sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env --profile front up -d --build
   --wait change-proposals front`.
6. Send `/start` to `@danoefront_agent`, then the public Visa test number (CARD in
   `services/hermes/front/tests/test_cardblock.py`) to front only: the message disappears and a notice comes. The
   `submit` path was tested on 1 Nov with a one-shot, `sudo docker exec personal-agent-front-1 hermes chat --oneshot -q
   "..."` (the `hermes` shim drops to uid 10000): proposal #2 appeared in the control bot.
- Logs: `/opt/personal-agent-data/hermes-front/logs/` (`agent.log`, `gateway.log`, `errors.log`); the data directory is
  root-only, so use `sudo` with absolute paths (`cd` into it fails).
- Memory: a fact front wants to keep waits for the owner in its own chat: `/memory pending` lists them,
  `/memory approve <id>` keeps one, `/memory reject <id>` drops it.
- After a change to `services/hermes/front/`: rsync as `make deploy` does, then the step 5 command with `front` only.
- Stop: the same compose command with `--profile front stop front change-proposals`.

## Restore
Always restore to a scratch directory, verify the ledger, then copy deliberately.

## Secrets rotation
Telegram: BotFather `/revoke`, then `make secret-set`.

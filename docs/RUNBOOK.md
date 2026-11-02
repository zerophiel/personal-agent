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
  risk and rollback; Setujui/Tolak work once. Approved means recorded in `control-state/approved/`; since the applier's
  install (2026-11-01 23:23 WIB, section Applier) an approved front change is applied, and the card says whether a tap
  applies it. Since control v3 (deployed 2026-11-01 23:22 WIB) control posts the diff it computed itself before every
  card.
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

## Comms zone (M4, built 2026-11-02, never started)
comms: Hermes on Haiku 5.5 with the six tools of two brokers: gmail-broker (search, read, the `Comms/` labels, reply
drafts the owner sends from Gmail) and calendar-broker (the primary calendar's events, read-only). No shell, code, files,
browser, web, memory or skills, and nothing is sent (`docs/SECURITY.md`, comms zone). It lives in
`compose/docker-compose.comms.yml` behind the `comms` profile; `make deploy` passes the main file alone, so it never
builds, starts or stops comms. What is built are conservative defaults; the owner's choices are open question 18 in
`docs/PROGRESS.md`. First start, in order (none done yet; 1-3 are the owner's):
1. Google (`docs/GMAIL_OAUTH.md`, "Zona comms"): the comms OAuth client, on the VPS as `google_comms_client`, and the
   two consents from the laptop: `bash scripts/gmail-renew.sh ~/client_secret_comms.json gmail_comms_token`, then the
   same with `calendar_comms_token`.
2. BotFather: a fourth bot for comms (username ending in `bot`), Bot Settings -> Allow Groups -> off; then
   `make secret-set NAME=telegram_comms_token`.
3. Anthropic Console: a third workspace for comms with a USD 10 monthly limit and a key from it; then
   `make secret-set NAME=anthropic_comms_key`.
4. `make secret-gen NAME=gmail_broker_mcp_token TYPE=token` and `make secret-gen NAME=calendar_broker_mcp_token
   TYPE=token`.
5. `make deploy` if the M4 files are not on the VPS yet (it also makes `hermes-comms` through `scripts/data-dirs.sh`),
   then on the VPS `cd /opt/personal-agent && sudo bash scripts/render-comms-env.sh` (it refuses another zone's key or
   bot).
6. Recreate squid-comms once, so it reads the `comms.conf` of M4 (a file bind mount keeps the file the container
   started with, and rsync writes a new one): `sudo docker compose -f compose/docker-compose.yml --env-file
   config/stack.env up -d --no-deps --force-recreate squid-comms`. Until then the runtime map shows squid-comms's config
   as different from the repo; harmless, since nothing uses squid-comms before comms runs.
7. Start: `sudo docker compose -f compose/docker-compose.yml -f compose/docker-compose.comms.yml --env-file
   config/stack.env --profile comms up -d --build squid-google gmail-broker calendar-broker comms`.
8. Send `/start` to the comms bot, then ask for this week's mail and tomorrow's events: a bank email must not come up.
- Logs: `/opt/personal-agent-data/hermes-comms/logs/` (root-only, `sudo` with absolute paths, as front); the brokers log
  errors only (`sudo docker logs personal-agent-gmail-broker-1`, `personal-agent-calendar-broker-1`).
- After a change to `services/hermes/comms/` or `services/comms-brokers/`: rsync as `make deploy` does, then the step 7
  command with the changed services; `/new` to the comms bot after a change to its `config.yaml` or `SOUL.md`.
- Google tokens: in Testing mode both run out 7 days after their consent. Renew both with step 1's commands before
  then; each broker reads its token file again before every refresh, so no restart. A refused token reaches the owner
  as comms's answer, which says to renew it from the laptop; no host check watches these tokens yet.
- Once comms runs, compose commands with the main file alone (`make deploy`, the applier) warn about orphan
  containers: the comms ones, which they leave alone (nothing here uses `--remove-orphans`). `scripts/prune.sh` knows
  only the main file: while comms is stopped, the weekly prune removes the broker images, and step 7's `--build` makes
  them again.
- Stop: the step 7 command with `stop comms gmail-broker calendar-broker squid-google` in place of `up ...`.

## Applier (M3, installed 2026-11-01 23:23 WIB)
`services/applier` applies a front change the owner approved in control (contract in `docs/SECURITY.md`). Its units are
in `services/applier/systemd/`, not `host/`, so `make deploy` never enables them.
- Install (done 2026-11-01 23:22-23:24 WIB on the owner's go-ahead at the M3 gate; again only after an uninstall, and
  only with the owner's go-ahead):
  1. `make deploy`: it carries the applier, control with its diff and new mounts, and the data folders
     (`scripts/data-dirs.sh` creates `applier/` and `applier/outcome/`).
  2. On the VPS: `cd /opt/personal-agent && sudo bash services/applier/install.sh`. The host check runs first, changes
     nothing and stops at the first FAIL; then the install time is recorded, `pa-applier.path` and `pa-applier.timer`
     are enabled and one run skips the approvals from before (the test #1). A FAIL on `tests/test_zones.py` with
     `No module named 'yaml'`: `sudo apt install python3-yaml` (present on 2026-11-01: PyYAML 6.0.1).
  3. From then on the card says the applier applies exactly the diff above it. After an applied change to front's
     `config.yaml` or `SOUL.md`, `/new` to `@danoefront_agent` (control's message says so).
- Look: `journalctl -u pa-applier.service -n 50 --no-pager`; `sudo ls /opt/personal-agent-data/applier/applied
  /opt/personal-agent-data/applier/failed /opt/personal-agent-data/applier/skipped`. A record holds hashes and reasons;
  `backup/` holds the old files (root only; do not print).
- Deploying while it is installed: when `make deploy` refuses with "applied on the VPS but not in this checkout", run
  `make applied-pull` (one commit per applied change), push, then `make deploy` again. A deploy that stopped halfway
  leaves the hold: `bash scripts/deploy-guard.sh end ubuntu@<vps>` (the applier ignores a hold older than 30 minutes).
- "pengembaliannya juga gagal ... perlu manusia" (rollback_failed): `sudo cat
  /opt/personal-agent-data/applier/failed/<id>.json` lists each file's `sha256_before` and `sha256_after`; compare them
  with `sudo sha256sum /opt/personal-agent/<path>`. From `/opt/personal-agent`, with
  `C="sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env --profile front"`:
  - equal to before: the old files are back; start the service: `$C up -d --no-deps --force-recreate --wait <service>`
    (`front` or `squid-front`, from the record);
  - equal to after: put the old files back, then the same command:
    `sudo python3 -I -c 'import base64, json, sys; [open("/opt/personal-agent/" + f["path"], "wb").write(base64.b64decode(f["b64"])) for f in json.load(open(sys.argv[1]))["files"]]' /opt/personal-agent-data/applier/backup/<id>.json`;
  - neither: the file was changed after the apply started; compare it with the repo and decide by hand.
  The applier never tries an id again once it has a record.
- Uninstall: `sudo systemctl disable --now pa-applier.path pa-applier.timer`, `sudo rm
  /etc/systemd/system/pa-applier.service /etc/systemd/system/pa-applier.path /etc/systemd/system/pa-applier.timer`,
  `sudo systemctl daemon-reload`, then `sudo rm /opt/personal-agent-data/applier/outcome/applier.json`: control says
  again that nothing is applied automatically. The records stay.

## Restore
Always restore to a scratch directory, verify the ledger, then copy deliberately.

## Secrets rotation
Telegram: BotFather `/revoke`, then `make secret-set`.

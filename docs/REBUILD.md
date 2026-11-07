# Rebuild on another VPS

`~/personal-agent` is the base for moving the bots to any provider. Git holds the recipe: code, SOULs, configs, compose files,
host config, pinned versions. `private/`, which git ignores, holds the rest: a full plaintext copy of the VPS data and secrets,
so the ledger and with it all the tuning. This folder and an empty VPS bring back the same bots with nothing to tune again.

Paste this to an AI working in `~/personal-agent`:

> Rebuild bot ini ke VPS `<alamat>` dengan login `<user>`. Baca `CLAUDE.md` dan `docs/REBUILD.md`, ikuti urutannya persis, jangan
> menampilkan isi `private/`.

The way has run against test fakes and the live host, never on a real second host, by the owner's choice. `make bootstrap`,
`make restore` and the applier's host check are proven only by the first real move, so small fixes may be needed there. On
2026-11-06 the pinned images had not been built on any host, since the owner put that deploy off, so step 3 builds them first. Data,
keys and config stay whole in this folder meanwhile, and the old bot stops only after bootstrap, preflight and that build have passed.

## What lives where

| Where | What | On GitHub |
|---|---|---|
| code, `services/hermes/*` (SOUL, config, plugins), `compose/`, `config/`, `host/`, `scripts/`, `docs/`, `CLAUDE.md` | the recipe | yes |
| `private/vps/data/` | `/opt/personal-agent-data`: the ledger and its backups, the Hermes homes, statements, logs | no |
| `private/vps/secrets/` | `/opt/personal-agent-secrets`, with `restic.env`, the key to the R2 backups | no |
| `private/vps/host/` | the live host config, package versions, image digests, `pip freeze`, the owner and mode of every path | no |
| `private/vps/MIRROR.json` | when it was pulled, the commit, counts, check results; no values or file names | no |
| `private/.prev/` | the copy before that | no |
| `private/laptop/`, `private/knowledge/` | Google client secrets and the public key; Claude's memory and transcripts, the Hermes engine and its graph, the original brief (`docs/LAPTOP.md`) | no |

The folder is only as fresh as the last `make mirror`; its age shows in the context of every session. R2 can be newer: see Disaster.

## Rules for the whole way

- Nothing under `private/` is read, listed, searched or printed by an AI, with any tool. It moves only through `make mirror` and
  `make restore`, which print counts and statuses. When one of them stops, `private/mirror.log` and `private/restore.log` hold the
  details, with file names and the repository URL, so the owner reads those.
- **[owner's terminal]** marks a step that needs a password, a browser or a typed secret. An AI asks the owner to run it in their own
  terminal, not through the session's `!` prefix: an ssh password prompt does not work there, and output lands in the conversation.
- Long polling: a bot token is polled from one host at a time, and two hosts take messages from each other. So the old host is frozen
  in step 5, before anything starts on the new one. This is why the order below matters.
- Stop at the first failed step and read the line it printed. Up to step 18 the old host still holds everything: see Going back.
- Never start `pa-gmail-token.service`, `pa-ingest.service` or `pa-ingest-alert.service` by hand: they message the owner.
- Never make a new `vault_tools_key` on a restored host: it would leave the stored account numbers unreadable.
- No `-v` on `docker compose down`, no `docker volume rm`. Never print `docker compose config`; `--services` and `-q` are fine.

## Before step 1

- The new host: an empty Ubuntu 24.04 amd64 KVM machine with at least 2 vCPUs, 7 GB of memory and 40 GB of free disk.
  `make preflight` holds these numbers. If the provider has a cloud firewall, open 22/tcp; the bots use no other inbound port.
- The provider's first login must be root or have passwordless sudo.
- The laptop: `make venv` once, since `make mirror` opens one stored number with it to prove the key works (`docs/LAPTOP.md`).
- The third parties below: only the IP limits need action before the move.

## Third parties

| Service | What the move changes | What to check |
|---|---|---|
| Telegram (BotFather) | Nothing: same tokens, and long polling needs no address | Revoke only in the disaster path |
| Anthropic | Nothing: same keys, workspaces and limits | A key with an IP limit needs the new address before step 11. Some countries are refused: `make preflight` shows it |
| Google | Nothing: same OAuth client, token, Gmail label and filter | The token lasts 7 days in Testing mode: step 15 |
| Cloudflare R2 | Nothing until step 18 | A token with an IP limit needs the new address before `make timers`, and in the disaster path before `make snapshots` |
| Notion | Nothing: same token | Revoke only in the disaster path |
| GitHub | Nothing: the VPS never pulls; `make sync` copies from the laptop | |
| Docker Hub | Images are pulled by digest, anonymously | A shared address can hit the anonymous pull limit: wait and run `make images` again |

## The way

### Preparation: the old bot stays alive

1. Put the new address and login in `config/vps.env` and commit. From here every target reaches the new host. A command for the old
   host adds `VPS_HOST=<old address> VPS_USER=<old login>`.
2. `make bootstrap BOOTSTRAP_USER=<the provider's first login>`. **[owner's terminal]** if that login asks for a password.
   - It installs the packages and Docker at the pinned versions, makes the account of `config/vps.env` with
     `~/.ssh/id_ed25519.pub` (`BOOTSTRAP_KEY=` for another), and only after a proof from the laptop closes ssh and the firewall.
   - A reused address with a new host key: `ssh-keygen -R <new address>` first.
   - If the last proof fails, the provider's console opens it again:
     `rm -f /etc/ssh/sshd_config.d/00-hardening.conf && ufw disable && systemctl reload-or-restart ssh`.
   - After a full run root and passwords are closed, so a second run is `make bootstrap BOOTSTRAP_USER=<login>`.
   - The apt log is `/var/log/personal-agent-bootstrap.log` on the host.
3. `make preflight` must exit 0. If it cannot be made to, take another provider; the old bot has not been touched.
   Then `make sync` and `make images`: every image is pulled or built on the new host and nothing starts. A bad pin or a refused pull
   shows here, with the old bot still running.
4. `make applied-pull VPS_HOST=<old address> VPS_USER=<old login>`, review, `git push`. A record that does not fit shows now, while
   the bot lives.

### The move: the bot stops here

Tell the owner before step 5: a message sent to the vault or front bot from here until step 16 is lost, and has to be sent again
afterwards. When Hermes starts, it discards what was queued while it was offline (`docs/runtime/hermes.md`, the default of
`drop_pending_on_cold_boot`). The control bot does read what it missed.

5. Freeze the old host, in an ssh session to it:
   ```
   sudo systemctl disable --now $(systemctl list-unit-files 'pa-*.timer' 'pa-*.path' --no-legend | awk '{print $1}')
   while systemctl list-units 'pa-*.service' --state=active,activating --no-legend --no-pager | grep -q .; do sleep 5; done
   cd /opt/personal-agent
   sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env --profile front --profile jobs down
   sudo docker ps -q --filter label=com.docker.compose.project=personal-agent
   ```
   The last line must print nothing. If it prints containers, the comms zone was started after this was written: stop it with the
   command in `docs/RUNBOOK.md`, section Comms zone.
6. `make mirror VPS_HOST=<old address> VPS_USER=<old login>` must exit 0, and its `files:` line must say `host frozen`. Exit 3 means
   a database was carried raw, a host fact failed or a laptop file was not kept: stop and show the owner.
7. `make restore CONFIRM=<new address>`. It refuses a host with this project on it. After a broken connection, run it again.
8. `make applied-pull`, review, `git push`.
9. `make sync`
10. `make secrets-check`, then `make render-envs`.
    - A line for a missing secret says how to make it. A token that was revoked: **[owner's terminal]** `make secret-set NAME=<name>`
      first.
    - A note about a Hermes home's `.env` matters only for a rotated token: that line wins over the rendered env, and the note gives
      the command that removes it.
11. `make up`
12. `make front`
13. `make applier`. Its host check needs front, squid-front and Telegram connected, so it comes after them.
14. `make timers`, last of all: these start the morning jobs and the backups.
15. **[owner's terminal]** `bash scripts/gmail-renew.sh` from the laptop if the Gmail token is nearly out. The control bot warns from
    two days before; see `docs/GMAIL_OAUTH.md`.
16. `make verify` must exit 0. Then the owner messages each bot: `/ping` to `@danoecontrol_bot`, and a question each to
    `@danoevault_agent` and `@danoefront_agent`. No `/new` is needed, since no SOUL or config changed.

The comms zone stays off; start it only as `docs/RUNBOOK.md` says, section Comms zone.

### Close

17. `make applied-pull`, then `make runtime-map`. Review and commit `docs/runtime/`, run `/graphify . --update`, then `make mirror`
    and `git push`.
18. **[owner's terminal]** Delete the old host at its provider, then rotate the R2 key as below.

### Pushing

Steps 1, 4, 8 and 17 make normal commits in this checkout, on `main`. The owner pushes with `git push`. An AI that may not push to
`main` pushes the same commits to a branch and says so. Nothing waits for the push: `scripts/deploy-guard.sh` reads this checkout,
not GitHub.

## Going back

If something fails between steps 5 and 16:

1. If the new host has started anything, stop it first, in an ssh session there. The bots must not poll from two hosts:
   ```
   sudo systemctl disable --now $(systemctl list-unit-files 'pa-*.timer' 'pa-*.path' --no-legend | awk '{print $1}')
   cd /opt/personal-agent
   sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env --profile front --profile jobs down
   ```
   On a host that got no further than step 9, these lines complain that there is nothing to stop. That is fine.
2. Start the old host again, from the laptop:
   ```
   make up VPS_HOST=<old address> VPS_USER=<old login>
   make front VPS_HOST=<old address> VPS_USER=<old login>
   make applier VPS_HOST=<old address> VPS_USER=<old login>
   make timers VPS_HOST=<old address> VPS_USER=<old login>
   make verify VPS_HOST=<old address> VPS_USER=<old login>
   ```
3. `git revert` the commit of step 1, so that `config/vps.env` names the old host again.

The old host's data did not change while it was frozen. Whatever a bot wrote on the new host meanwhile stays there only: tell the
owner. The timers are persistent, so the runs missed during the freeze start at once.

A new try starts again at step 1. If step 7 has already placed the ledger, `make bootstrap` and `make restore` refuse that host:
ask the owner whether anything a bot wrote there is still needed, then reinstall the instance at the provider first.

## Disaster: the old host is gone

Skip steps 4 to 6 and keep the rest of the order, with these changes:

- After step 3, `make snapshots` lists the R2 snapshots and says whether the newest is newer than the copy. If it is, step 7 becomes
  `make restore-restic SNAPSHOT=<id> CONFIRM=<new address>`, and a snapshot that does not fit can be replaced by an older one.
  If the copy is newer, step 7 stays `make restore`.
- Step 16 is `make verify R2=1` after a snapshot: a difference from the copy is reported, not failed. If the snapshot was older than
  the copy, the `make mirror` of step 17 is `make mirror ALLOW_SHRINK=1`.
- If the old host may come back, delete the instance before step 11. If the provider cannot, rotate the bot tokens, the R2 key and the
  Notion token: a host that comes back would poll, back up and write to Notion with stale data.

## Rotating the R2 key

After a move the old host's disk may outlive the instance, so the key it held is replaced.

1. **[owner's terminal]** At Cloudflare, make a new R2 API token for the bucket.
2. **[owner's terminal]** On the new host, `sudo nano /opt/personal-agent-secrets/restic.env`, and replace the values of only
   `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. No quotes. `RESTIC_PASSWORD` stays as it is: no snapshot opens without it.
3. `make mirror`, so that the copy holds the new key.
4. `make snapshots`. It opens R2 with the copy's `restic.env`, so a list proves the new key works. Before step 3 it would only
   prove the old one.
5. **[owner's terminal]** Delete the old token at Cloudflare. A backup that fails from here shows in `make verify`, as `failed_units`.

## If the laptop is lost

`private/` holds every key in plaintext.

- Revoke at once: the bot tokens at BotFather, the Anthropic keys, the Google client and tokens, the R2 token, the Notion token. Put
  the new ones on the VPS with `make secret-set NAME=<name>`, then `make render-envs`, a restart of the service, and the recipe above
  for R2. `docs/GMAIL_OAUTH.md` has Google.
- Tell the owner what cannot be revoked: the ledger's stored account numbers are encrypted with `vault_tools_key`, which the copy
  holds, and nothing re-encrypts them under a new key yet.
- On a new laptop: clone the repo, set it up by `docs/LAPTOP.md` (the tools, a git identity, `make venv`), make an ssh key, add it
  through the provider's console (passwords are closed), then `make mirror`. That brings back `private/vps/` from the VPS. `private/laptop/` and `private/knowledge/` come back only from the
  owner's own copies: the Google client from its console, and the memory and transcripts not at all.
- If the laptop and the VPS are lost together, R2 stays locked unless `restic.env` was also kept elsewhere, for instance in a password
  manager.

## Not in the recipe

- Remaking the bots at BotFather or the Notion workspace from nothing. They do not depend on the host.
- A saved copy of the images: Hermes and squid come from Docker Hub by digest, and the rest build from the pinned base and locks.
- The network's MTU and subnets. A provider with an MTU below 1500 can make TLS hang inside containers; the compose files do not set one.
- Anything of the old provider: its agents, package mirrors and time servers stay behind. `make bootstrap` uses Ubuntu's and Docker's own.

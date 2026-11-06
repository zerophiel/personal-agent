# The laptop

`~/personal-agent` on the owner's laptop, Ubuntu in WSL, is where the recipe is edited and where the plaintext copy in `private/` lives.
This page is what a new laptop needs. `docs/REBUILD.md` holds what to do when one is lost, and what to revoke.

## Tools

- `git`, `make`, `python3`, `rsync`, `flock`, `ssh` and `uv`. Docker and restic run on the VPS only.
- `make venv`, once: `~/.venv-personal-agent`, the Python of `make test` and `make mirror`. It stays outside the repo, so it never
  reaches the VPS.
- graphify, for the project map in `CLAUDE.md`: `uv tool install graphifyy==0.9.99`, then `graphify install --platform claude`.
- The Gmail tool, once: `python3 -m venv ~/.venv-gmail && ~/.venv-gmail/bin/pip install google-auth-oauthlib`. It runs
  `scripts/gmail-renew.sh`, which needs the client secret below. WSL cannot start a browser: open the printed link in Windows.
- `gh auth login`, for pull requests.

## The ssh key

`make` reaches the VPS with the default key. The copy holds only the public half: `~/.ssh/id_ed25519` belongs to the laptop and may be
in use elsewhere. A new laptop makes a new key with `ssh-keygen -t ed25519`, and it goes into the `~/.ssh/authorized_keys` of the login in
`config/vps.env` through the provider's console, since passwords are closed.

## What comes back from `private/`

`make mirror` keeps these and never deletes from them. Only the owner brings them back, in their own terminal, since no AI reads
`private/`:

```
cd ~/personal-agent
install -m 0600 private/laptop/client_secret_ingest.json ~/
rsync -rlpt private/knowledge/claude-projects/ ~/.claude/projects/
mkdir -p ~/.graphify/repos/NousResearch
rsync -rlpt private/knowledge/hermes-engine/ ~/.graphify/repos/NousResearch/hermes-agent-v0.22.5/
rsync -rlpt --ignore-existing private/knowledge/graphify-out/ graphify-out/
```

- **`~/.claude/projects/`**: Claude's memory and the session transcripts. The folder name follows the checkout's path, as
  `-home-danoe-personal-agent`. With another home folder, rename it to match, or the memory is not found.
- **`hermes-agent-v0.22.5`**: the engine's source and its graph, which `CLAUDE.md` queries. It is too big for git.
- **`graphify-out/`**: what git does not hold, such as the extraction cache. `--ignore-existing` leaves the committed graph as it is.

## Keeping the copy safe

The folder holds every key in plaintext, and the Windows side can read WSL files. Both of these are the owner's own decision:

- Disk encryption on the laptop, for instance BitLocker.
- `restic.env` also in a password manager, copied from the owner's terminal. Then losing the laptop and the VPS together does not lock
  the R2 backups.

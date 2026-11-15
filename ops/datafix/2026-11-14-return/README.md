# Return from kimiclaw (2026-11-14)

From 9 to 14 Nov 2026 the vault bot ran on a second server, an OpenClaw host ("kimi"), while the original VPS ("orig")
stood frozen with its 9 Nov data. These scripts bring the vault data written on kimi home to orig: Tahap A and B of the
return plan in `docs/PROGRESS.md`.

| Script | Step | What it does |
|---|---|---|
| `probe.py` | A1, A2, B1 | Read-only report of one host as JSON: row hashes, counts, schemas, short codes, hashed file names, secret names. |
| `compare.py` | A2, A4 | `summary` of one report. `diff` of orig's and kimi's: the plan's data gate, the plan conditions that have a known handling and wait for the owner's decision, and what needs the owner's eye. |
| `stage.py` | B2 | Streams kimi's frozen databases and ingest folder into a new root-only staging folder on orig, checks them against kimi's frozen report, and writes `MANIFEST.json`. Orig's live data is not touched. |
| `install.py` | B4 | With every container down: keeps orig's databases as `<name>.bak-pre-return-<date>`, puts the staged copies in place with the old owner and mode, adds the new ingest files, and checks the result in place. `--check` only checks; `--rollback` puts the 9 Nov data back. |

## Order

1. A1 and A2: `probe.py kimi KIMI kimi.json` and `probe.py orig ORIG orig.json`. A4: `compare.py diff orig.json
   kimi.json`. The owner reads the report, then gives the OK for Tahap B or not.
2. B1: kimi is frozen by hand: its finance timers and `vault-tools.service` disabled, nothing holding a database,
   OpenClaw left running. Then `probe.py kimi KIMI kimi_frozen.json`.
3. B2: `stage.py KIMI ORIG kimi_frozen.json <stamp>`, with a new stamp for each attempt.
4. B3: the owner revokes the vault bot's token in BotFather and sets the new one with
   `make secret-set NAME=telegram_vault_token`.
5. B4: `install.py ORIG <stamp> orig.json result.json --check`, then the same without `--check`. `--rollback` with the
   same result file undoes it.
6. B5: the stack starts from its images (`up -d --no-build --pull never`). The `pa-ingest` and `pa-gmail-token` timers
   have their stamps cleared before they are enabled, so neither runs as a catch-up.

## Addresses and output

`KIMI` and `ORIG` are `user@host` and never typed. Orig's address comes from `config/vps.env`. Kimi's comes from the
Tailscale peer list, checked against the `config/vps.env` of Kimi's local commit `bae2167`. `PA_SSH` replaces the ssh
command (the tests use it). The output holds counts, statuses, sizes and short hashes only, and is read through
`ops/privacy/mask.py` and a filter for IP addresses.

## Tests

The scripts were tested on the laptop on 14 and 15 Nov, on two fake hosts built with the repo's ledger schema, through
stand-ins for ssh, sudo, docker and systemctl. The harness stayed in the session's temporary folder. The tests covered:

- stage, install and rollback, end to end;
- the file-copy way, for a Python without sqlite3 `serialize`;
- each stop, with the data left as it was:
  - a file with the same name and other content;
  - `_events.jsonl` that is not a prefix;
  - the live ledger changed after its report;
  - the staged copy changed after staging;
  - kimi changed after its frozen report;
  - an existing staging folder;
  - a running container;
  - an active data unit.

`compare.py` was checked on reports changed by hand: one change for each gate, decision and attention branch, and the
kimi-only parts of a report (units, menu files, cron jobs, listings). Its `summary` ran in full on orig's real report.

## Status

The scripts are written and tested. On a host, only the read-only `probe.py orig` has run (A2, 14 Nov). Tahap B waits
for the owner's OK.

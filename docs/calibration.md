# Bot calibration runbook (manual, on the owner's request)

The owner asks for a calibration ("kalibrasi bot"); there is no scheduler on purpose: an unattended agent would need SSH and
deploy rights to the finance VPS without anyone watching. Goal: the bot's money answers stay correct. Numbers are computed by
vault-tools (tested, reconciled, audited); the model routes tools and relays results, so calibration looks for the places where
the model or the data drifted.

## 1. Read the state
- `docs/PROGRESS.md` (open questions, last calibration), open PR, `git log`.
- Owner's rules that are not negotiable (also in `services/hermes/vault/SOUL.md`): anything for the children (school, lessons,
  Rockstar Gym = Gracia's gym) is never proposed as a cut; games are the owner's own spending; apps: ask per app; living money
  (`living_reserve`, the owner's choice: Rp 7.546.005 since 2026-10-28) is protected; the owner pays everything on the 1st and wants no proactive reminders.

## 2. Spend and quality (read-only)
- `ops/calibration/bot_usage.py`: cost per day and source at list prices. Hermes shows `cost_status: unknown` for
  claude-sonnet-5-5, so compare with the USD 45/month vault limit by hand. Calibration one-shots appear as source `oneshot`.
- `ops/calibration/bot_quality.py`: tool errors and replies that apologise or correct themselves. Read each flagged reply in
  context. Every real mistake gets a root cause and a fix in code (preferred) or SOUL, with a regression test.
- Replies the number guard flagged since the last calibration ("⚠️ Cek angka", appended by the cardguard plugin): each
  holds a number no tool result or owner message of that session gave, usually the model's own sum, difference or reading
  of a photo. The fix is a tool result that carries that figure (2026-11-01: the JUMLAH line, "Yang bisa dipakai",
  `recorded`).

## 3. Data (read-only)
- `/periksa` in Telegram or `periksa_data`: statements that do not reconcile, missing statements, unpaid past-due bills,
  subscriptions recorded vs charged, stopped subscriptions still charged, instalments gone from the statement, old pot balance.
- `ops/calibration/recurring_charges.py`: per-month table of recurring merchants; confirm open items with the owner, who
  decides what is recurring, ended, one-off, or `wajib`.

## 4. Change and verify
- Worktree only; tests: `cd services/vault-tools && python -W ignore -I -m unittest discover -s tests` (plus
  `services/hermes/vault/tests`, `services/ingest-gmail/tests`, root `tests`).
- `ops/calibration/dry_run.py` on a copy of the live ledger: every statement must re-read as `cocok`; read the audit and the
  plan for the coming 1st.

## 5. Deploy (from the worktree root)
1. `rsync -az --delete --exclude .git --exclude .claude ./ ubuntu@43.157.242.194:/opt/personal-agent/`
2. Ledger backup with the SQLite backup API (consistent under WAL), e.g.
   `sudo docker exec personal-agent-vault-tools-1 python -c "import sqlite3; s=sqlite3.connect('/data/ledger.db'); d=sqlite3.connect('/data/ledger.db.bak-<name>'); s.backup(d)"`
3. `cd /opt/personal-agent && sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env up -d --build vault-tools`
4. Data changes as a script piped into `docker exec -i personal-agent-vault-tools-1 python -`, each change asserted after.
5. Config, SOUL or plugin changed: `... restart vault`; the owner sends `/new` in Telegram.

## 6. Test economically (each one-shot costs about USD 0.5-1)
- At most two: `sudo docker exec personal-agent-vault-1 hermes chat --oneshot -q "UJI KALIBRASI (jangan mencatat atau mengubah apa pun). ..."`.
  Never let a test call a writing tool on real data (e.g. `saldo_rekening` on `jago-harian` re-anchors the month's daily
  money to the balance given).
- Check that every number in the answer is in a tool result of that turn.

## 7. Report
Owner report in Bahasa Indonesia (what was wrong, what changed, numbers from code, decisions only the owner can make);
update `docs/PROGRESS.md`; commit and push the branch.

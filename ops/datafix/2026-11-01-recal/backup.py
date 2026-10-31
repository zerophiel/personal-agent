"""Ledger backup before the 1 Nov recalibration deploy, run by deploy.sh in the vault-tools container. The deploy changes
code only (what the tools say), no data; the backup is the way back all the same. Safe to run again: a backup left by an
earlier run is checked, not replaced."""
import os, sqlite3

DB, BAK = "/data/ledger.db", "/data/ledger.db.bak-pre-recal"

if not os.path.exists(BAK):
    src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    dst = sqlite3.connect(BAK)
    src.backup(dst)                      # the SQLite API: a consistent copy while the server runs
    dst.close()
    src.close()
b = sqlite3.connect(f"file:{BAK}?mode=ro", uri=True)
ok = b.execute("PRAGMA integrity_check").fetchone()[0]
rows = {t: b.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("transactions", "plans", "balance_reports")}
print("backup", BAK, "| integrity", ok, "| schema", b.execute("PRAGMA user_version").fetchone()[0], "|", rows)
assert ok == "ok", "backup is damaged: stop"

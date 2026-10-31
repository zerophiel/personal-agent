"""Data fix for the daily-money pace (a1ee6d3, 7145b14), run by deploy.sh in the vault-tools container on the code still
deployed, BEFORE the new code: with `living_leftover_spent` missing, the next `sisa_uang_harian` would take every purchase since the
payday as already out of the leftover. Safe to run again: checks first, one backup, one write, nothing when already done."""
import os, sqlite3, sys
sys.path.insert(0, "/app")
from vault_tools import health, tools
from vault_tools.ledger import connect

DRY = False
DB, BAK = "/data/ledger.db", "/data/ledger.db.bak-pre-pace-fix"

# 1. read only: the payday's reading (30 Oct 15:27, 4.718.116) came after Warkop Dani 17.000 (#2441, recorded 15:23);
#    no other cash purchase dated 30 Oct was recorded before it
ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ro.row_factory = sqlite3.Row
left, payday, done = (tools.get_threshold(ro, k) for k in ("living_leftover", "living_leftover_payday", "living_leftover_spent"))
assert (left, payday) == (4718116, 20261030), ("the leftover changed since the dry run", left, payday)
rows = [r for r in ro.execute(
    "SELECT id, merchant, amount, category FROM transactions WHERE amount < 0 AND merged_into IS NULL AND card_id IS NULL"
    " AND txn_date = '2026-10-30' AND id <= 2441") if health.is_discretionary(r["category"])]
before = -sum(r["amount"] for r in rows)
assert [r["id"] for r in rows] == [2441] and before == 17000, ([tuple(r) for r in rows], before)
ro.close()
if done == before:
    print("already done: living_leftover_spent =", done)
    sys.exit(0)
assert done is None, ("living_leftover_spent holds another value", done)
if DRY:
    print("dry run ok: would back up to", BAK, "and set living_leftover_spent =", before)
    sys.exit(0)

# 2. backup with the SQLite API (safe while the server runs); one left by an interrupted run is checked, not replaced
if not os.path.exists(BAK):
    src, dst = sqlite3.connect(DB), sqlite3.connect(BAK)
    src.backup(dst)
    dst.close()
    src.close()
chk = sqlite3.connect(f"file:{BAK}?mode=ro", uri=True)
ok = chk.execute("PRAGMA integrity_check").fetchone()[0]
assert ok == "ok", ok
print("backup", BAK, ok, "| transactions", chk.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
      "| plans", chk.execute("SELECT COUNT(*) FROM plans").fetchone()[0])
chk.close()

# 3. the one write
conn = connect(DB)
print(tools.set_threshold(conn, "living_leftover_spent", before))

"""Data fix for the daily-account anchor (e5d494c, 60ae046), run by deploy.sh in the vault-tools container AFTER the new
code is built: it stores the owner's 1 Nov reading of the daily pocket (7.051.352, told in the Claude Code session, not to
the bot) with record_account_balance, which only the new code anchors. Safe to run again: checks first, one backup, one
write, nothing when already done."""
import os, sqlite3, sys
from datetime import date
sys.path.insert(0, "/app")
from vault_tools import health, tools
from vault_tools.ledger import connect

DRY = False
DB, BAK = "/data/ledger.db", "/data/ledger.db.bak-pre-pocket-balance"
DAY, ALIAS, BALANCE, MARK = date(2026, 11, 1), "jago-harian", 7051352, 2445

assert hasattr(health, "living_anchor"), "the old code is still running: rebuild vault-tools first"

# 1. read only: nothing recorded since the reading (the last row then was #2445, ANKER 31 Oct), the payday's top-up is
#    marked done, and the anchor is not there yet
ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ro.row_factory = sqlite3.Row
rid = tools.get_threshold(ro, "living_balance_report")
if rid is not None:
    r = ro.execute("SELECT as_of, balance FROM balance_reports WHERE id=?", (rid,)).fetchone()
    if r is not None and (r["as_of"], r["balance"]) == (DAY.isoformat(), BALANCE):
        print("already done: living_balance_report =", rid, "| mark", tools.get_threshold(ro, "living_balance_mark"))
        sys.exit(0)
    sys.exit(f"STOP: another daily-account reading is stored ({rid}); look before writing")
top = ro.execute("SELECT MAX(id) FROM transactions").fetchone()[0]
if top != MARK:     # a row recorded after the reading must not fall under the mark: store it by hand after a look
    print("STOP: transactions recorded since the reading:",
          [tuple(x) for x in ro.execute("SELECT id, txn_date, source, amount < 0 FROM transactions WHERE id > ?", (MARK,))])
    sys.exit(1)
assert ro.execute("SELECT 1 FROM plan_progress WHERE payday='2026-10-30' AND item='uang-harian'").fetchone(), "top-up not done"
plans = ro.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
ro.close()
if DRY:
    print("dry run ok: would back up to", BAK, "and store", ALIAS, BALANCE, "for", DAY, "| plans", plans)
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

# 3. the one write: the same tool the bot calls (saldo_rekening)
conn = connect(DB)
print(tools.record_account_balance(conn, DAY, ALIAS, BALANCE))

"""Read only, after the deploy: the new code runs and the month follows the owner's 1 Nov reading of the daily pocket."""
import sqlite3, sys
sys.path.insert(0, "/app")
from vault_tools import health, tools

assert hasattr(health, "living_anchor"), "the old code is still running"
src = sqlite3.connect("file:/data/ledger.db?mode=ro", uri=True)
mem = sqlite3.connect(":memory:")       # payday_status may store a plan row: never on the live ledger from here
src.backup(mem)
src.close()
mem.row_factory = sqlite3.Row
mem.execute("PRAGMA foreign_keys = ON")
today = tools.wib_today()
p = health.spending_pace(mem, today)
print("pace", today, {k: p[k] for k in ("allowance", "spent", "remaining", "pct_used", "status", "correction")})
print("reading", p["reading"])
assert p["reading"] and (p["reading"]["balance"], p["reading"]["as_of"]) == (7051352, "2026-11-01"), p["reading"]
assert tools.get_threshold(mem, "living_balance_mark") == 2445
if today.isoformat() == "2026-11-01" and mem.execute("SELECT MAX(id) FROM transactions").fetchone()[0] == 2445:
    assert (p["remaining"], p["correction"], p["allowance"], p["spent"], p["status"]) == (7051352, 129422, 7675427, 624075, "ok"), p
plans = mem.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
status = tools.payday_status(mem, today)
assert "saldo jago-harian Rp 7.051.352" in status
line = [x for x in tools.data_overview(mem, today).splitlines() if x.startswith("UANG HARIAN BULAN INI")]
print("plans", plans, "| overview:", line)
assert line and "mengikuti saldo jago-harian Rp 7.051.352" in line[0]
print("alert after a purchase now:", health.alerts_for(mem, today, "belanja", today) or "none")
print("VERIFIED")

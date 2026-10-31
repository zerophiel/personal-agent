"""Read only, after the deploy: the new code runs and the daily money is the top-up plus the leftover."""
import sqlite3, sys
sys.path.insert(0, "/app")
from vault_tools import health, tools

assert hasattr(health, "cash_spent"), "the old code is still running"
src = sqlite3.connect("file:/data/ledger.db?mode=ro", uri=True)
mem = sqlite3.connect(":memory:")
src.backup(mem)
mem.row_factory = sqlite3.Row
mem.execute("PRAGMA foreign_keys = ON")
today = tools.wib_today()
p = health.spending_pace(mem, today)
print("pace", today, p)
assert (p["allowance"], p["from_salary"], p["leftover"], p["spent_before_leftover"]) == (7546005, 2827889, 4718116, 17000), p
print("plans", mem.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
      "| living_leftover_spent", tools.get_threshold(mem, "living_leftover_spent"))
print("alert after a purchase now:", health.alerts_for(mem, today, "belanja", today) or "none")
print("VERIFIED")

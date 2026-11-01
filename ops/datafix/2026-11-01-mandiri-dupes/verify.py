"""Read only, after the deploy: the new code runs, every mutation file agrees with the ledger again, the 17 doubled rows are
gone and logged, and the audit has no mutation finding. Prints dates, counts and amounts, no merchant text."""
import sqlite3, sys
from datetime import date
sys.path.insert(0, "/app")
from vault_tools import audit, mutations

assert hasattr(mutations, "ledger_gap"), "the old code is still running"
src = sqlite3.connect("file:/data/ledger.db?mode=ro", uri=True)
mem = sqlite3.connect(":memory:")       # nothing below writes, but the audit and cashflow never run on the live ledger here
src.backup(mem)
src.close()
mem.row_factory = sqlite3.Row
acc = {r["id"]: r["alias"] for r in mem.execute("SELECT id, alias FROM accounts")}
bad = 0
for f in mem.execute("SELECT * FROM mutation_files WHERE opening_balance IS NOT NULL AND closing_balance IS NOT NULL"
                     " ORDER BY account_id, period_start, period_end"):
    held, g = mutations.ledger_gap(mem, f["account_id"], f["period_start"], f["period_end"], f["opening_balance"], f["closing_balance"])
    if abs(g) > mutations.ROUNDING_TOLERANCE:
        bad += 1
        print("MISMATCH", acc[f["account_id"]], f["period_start"], f["period_end"], g)
print("mutation files checked against the ledger, mismatches:", bad)
left = mem.execute("SELECT COUNT(*) FROM transactions WHERE id BETWEEN 2449 AND 2465").fetchone()[0]
logged = mem.execute("SELECT COUNT(*) FROM change_log WHERE tbl='transactions' AND action='hapus' AND reason LIKE 'baris ganda%'").fetchone()[0]
print("doubled rows left:", left, "| logged as removed:", logged)
print("e-statement file:", tuple(mem.execute("SELECT row_count, new_rows, reconciled, recon_diff FROM mutation_files m JOIN accounts a"
                                              " ON a.id = m.account_id WHERE a.alias='mandiri-utama' AND period_start='2026-10-01'"
                                              " AND period_end='2026-10-31'").fetchone()))
c = mutations.cashflow(mem, "2026-10")
print("cashflow 2026-10: rows", c["rows"], "income", c["income"], "expenses", c["expenses"], "uncategorized",
      dict(c["by_category"]).get("belum dikategorikan", 0), "unverified", c["unverified"])
findings = audit.run(mem, date.today())
print("audit: bad", sum(1 for s, _ in findings if s == "bad"), "warn", sum(1 for s, _ in findings if s == "warn"), "info",
      sum(1 for s, _ in findings if s == "info"), "| mutation findings", sum(1 for _, t in findings if t.startswith("Mutasi")))

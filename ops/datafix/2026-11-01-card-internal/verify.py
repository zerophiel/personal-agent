"""Read only, after the deploy: the new code runs, no stored rule or row holds a repayment to an own card or the Jago
main-pocket interest as 'transfer_internal', the changes are in change_log, every mutation file still agrees with the
ledger, and the cashflow of August to October with the audit counts. Prints counts and amounts, no merchant text."""
import sqlite3, sys
from collections import Counter
from datetime import date
sys.path.insert(0, "/app")
from vault_tools import audit, living, mutations

assert hasattr(mutations, "card_paid"), "the old code is still running"
src = sqlite3.connect("file:/data/ledger.db?mode=ro", uri=True)
mem = sqlite3.connect(":memory:")       # nothing below writes, but the audit and cashflow never run on the live ledger here
src.backup(mem)
src.close()
mem.row_factory = sqlite3.Row
cards = mutations.own_cards(mem)
own = [r["pattern"] for r in mem.execute("SELECT pattern FROM category_rules WHERE category=?", (mutations.INTERNAL,))]
print("own-move rules naming an own card:", sum(1 for p in own if mutations.card_paid(p, cards)),
      "| main-pocket rules still own moves:", sum(1 for p in own if p.startswith("main pocket ") and "interest" in p))
rows = mem.execute("SELECT merchant FROM transactions WHERE category=? AND merged_into IS NULL", (mutations.INTERNAL,)).fetchall()
print("own-move rows paying an own card:", sum(1 for r in rows if mutations.card_paid(r["merchant"], cards)),
      "| main-pocket interest rows still own moves:",
      sum(1 for r in rows if mutations.normalize(r["merchant"]) in ("main pocket interest", "main pocket tax on interest")))
print("change_log:", dict(Counter(r["tbl"] for r in mem.execute(
    "SELECT tbl FROM change_log WHERE reason LIKE 'pembayaran kartu %' OR reason LIKE '%poket utama Jago%'"))))
bad = sum(1 for f in mem.execute("SELECT * FROM mutation_files WHERE opening_balance IS NOT NULL AND closing_balance IS NOT NULL")
          if abs(mutations.ledger_gap(mem, f["account_id"], f["period_start"], f["period_end"], f["opening_balance"],
                                      f["closing_balance"])[1]) > mutations.ROUNDING_TOLERANCE)
print("mutation files that disagree with the ledger:", bad)
lv = living.monthly(mem, date.today())
for m in ("2026-08", "2026-09", "2026-10"):
    c = mutations.cashflow(mem, m)
    print(f"cashflow {m}: income {c['income']} expenses {c['expenses']} | living cost (cash) {lv.get(m, {}).get('cash')}"
          f" | unverified {c['unverified']}")
findings = audit.run(mem, date.today())
print("audit: bad", sum(1 for s, _ in findings if s == "bad"), "warn", sum(1 for s, _ in findings if s == "warn"), "info",
      sum(1 for s, _ in findings if s == "info"))

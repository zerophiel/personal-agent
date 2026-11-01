"""Data fix for card repayments held as moves between own accounts (found 1 Nov): from 52e70ac (28 Oct) the category
suggestions read a transfer to one of the owner's card numbers as 'transfer_internal', so the September repayments of
four cards left the month's expenses, and their stored rules would have done the same to every later payment. A card's
spending reaches the bank cashflow only as its repayment, so these become 'wajib:kartu'. Jago's main-pocket interest and
its tax were held the same way; they become 'bunga' and 'biaya-bank'. Run by deploy.sh in the vault-tools container after
the new code is built: the same detector (mutations.card_paid) guards the category tools from then on. Checks first, one
backup, then one transaction in which every rule and row changed is logged in change_log. DRY = True does all of it on
an in-memory copy. Safe to run again."""
import os, sqlite3, sys
from collections import Counter, defaultdict
from datetime import date
sys.path.insert(0, "/app")
from vault_tools import changelog, living
from vault_tools.ledger import connect
from vault_tools.mutations import CARD_BILL, INTERNAL, card_paid, cashflow, normalize, own_cards

DRY = False
DB, BAK = "/data/ledger.db", "/data/ledger.db.bak-pre-card-internal"
CARDS = {"cimb-9888", "dbs-5685", "hsbc-5915", "mega-5855"}    # whose rules say 'transfer_internal' (the 1 Nov probe)
SEPTEMBER = "2026-09"                                           # each of them has exactly one repayment held so there
POCKET = {"main pocket interest": "bunga", "main pocket tax on interest": "biaya-bank"}
WHY_CARD = "pembayaran kartu {}, bukan pindah dana antar rekening sendiri (usulan kategori keliru sejak 28 Okt)"
WHY_POCKET = {"bunga": "bunga poket utama Jago, bukan pindah antar poket",
              "biaya-bank": "pajak bunga poket utama Jago, bukan pindah antar poket"}
MONTHS = ("2026-08", "2026-09", "2026-10")


def plan(conn):
    """([(pattern, new, card)], [(row, new, card)]) to change, card None for the pocket ones; both empty when already
    done. Stops on anything unexpected."""
    cards = own_cards(conn)
    rows = conn.execute("SELECT * FROM transactions WHERE source IN ('mutation','receipt') AND merged_into IS NULL"
                        " ORDER BY id").fetchall()
    by_key = defaultdict(list)
    for r in rows:
        by_key[normalize(r["merchant"])].append(r)
    rules = []
    for rule in conn.execute("SELECT pattern FROM category_rules WHERE category=? ORDER BY pattern", (INTERNAL,)).fetchall():
        p = rule["pattern"]
        if p in POCKET:
            rules.append((p, POCKET[p], None))
            continue
        held, named = by_key.get(p, []), card_paid(p, cards)
        paid = {card_paid(r["merchant"], cards) for r in held} | ({named} if named else set())
        if paid <= {None}:
            continue
        # the key must hold one card's repayments and nothing else: an own move under the same key means look first
        assert None not in paid and len(paid) == 1, f"STOP: rule '{p}' holds {paid}; look before writing"
        assert all(r["amount"] < 0 for r in held), f"STOP: rule '{p}' holds money in from a card; look before writing"
        rules.append((p, CARD_BILL, paid.pop()))
    fixed = {p: new for p, new, _ in rules}
    todo = []
    for r in rows:
        if r["category"] != INTERNAL:
            continue
        k, card = normalize(r["merchant"]), card_paid(r["merchant"], cards)
        if card:
            assert r["amount"] < 0, f"STOP: #{r['id']} is money in from {card}; look before writing"
            assert fixed.get(k) == CARD_BILL, f"STOP: #{r['id']} pays {card} but no rule made it an own move; look first"
            todo.append((r, CARD_BILL, card))
        elif k in POCKET:
            todo.append((r, POCKET[k], None))
    if not rules and not todo:
        return [], []
    got = {c for _, new, c in rules if new == CARD_BILL}
    assert got == CARDS, f"STOP: the card rules to change are for {sorted(got)}, the probe found {sorted(CARDS)}"
    sept = sorted(c for r, new, c in todo if new == CARD_BILL and r["txn_date"][:7] == SEPTEMBER)
    assert sept == sorted(CARDS), f"STOP: September holds card rows for {sept}"
    ids = [r["id"] for r, _, _ in todo]
    refs = conn.execute(f"SELECT COUNT(*) FROM transactions WHERE merged_into IN ({','.join('?' * len(ids))})", ids).fetchone()[0]
    assert refs == 0, "STOP: a receipt is merged into one of the rows; look before writing"
    return rules, todo


def reason(new, card):
    return WHY_CARD.format(card) if card else WHY_POCKET[new]


def show(conn, label):
    lv = living.monthly(conn, date(2026, 11, 1))
    for m in MONTHS:
        c = cashflow(conn, m)
        print(f"{label} {m}: income {c['income']} expenses {c['expenses']} | living cost (cash) {lv.get(m, {}).get('cash')}")


def print_plan(rules, todo):
    print("rules to change:", len(rules), dict(Counter(card or new for _, new, card in rules)))
    per = defaultdict(lambda: [0, 0])
    for r, new, card in todo:
        per[(card or new, r["txn_date"][:7])][0] += 1
        per[(card or new, r["txn_date"][:7])][1] += r["amount"]
    for k in sorted(per):
        print("  rows", k, "n", per[k][0], "sum", per[k][1])


# 1. read only: what changes, checked
ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ro.row_factory = sqlite3.Row
rules, todo = plan(ro)
show(ro, "now")
if not rules and not todo:
    print("already done: no rule or row holds an own card's repayment or the main-pocket interest as transfer_internal")
    sys.exit(0)
print_plan(rules, todo)

# 2. the target: an in-memory copy (DRY) or the ledger after a backup with the SQLite API (safe while the server runs);
#    a backup left by an interrupted run is checked, not replaced
if DRY:
    conn = sqlite3.connect(":memory:")
    ro.backup(conn)
    conn.row_factory = sqlite3.Row
    print("DRY: on an in-memory copy, nothing is written")
else:
    if not os.path.exists(BAK):
        src, dst = sqlite3.connect(DB), sqlite3.connect(BAK)
        src.backup(dst)
        dst.close()
        src.close()
    chk = sqlite3.connect(f"file:{BAK}?mode=ro", uri=True)
    ok = chk.execute("PRAGMA integrity_check").fetchone()[0]
    assert ok == "ok", ok
    print("backup", BAK, ok, "| transactions", chk.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
    chk.close()
    conn = connect(DB)
ro.close()

# 3. one transaction: re-checked on the target, each rule and row logged, then changed (status stays as it was)
rules, todo = plan(conn)
for p, new, card in rules:
    changelog.log(conn, "category_rules", p, "ubah", {"category": INTERNAL}, {"category": new}, reason(new, card))
    conn.execute("UPDATE category_rules SET category=? WHERE pattern=?", (new, p))
for r, new, card in todo:
    changelog.log(conn, "transactions", r["id"], "ubah", {"category": r["category"]}, {"category": new}, reason(new, card))
    conn.execute("UPDATE transactions SET category=? WHERE id=?", (new, r["id"]))
conn.commit()
show(conn, "after")
print("change_log rows written:", conn.execute("SELECT COUNT(*) FROM change_log WHERE reason LIKE 'pembayaran kartu %'"
                                               " OR reason LIKE '%poket utama Jago%'").fetchone()[0])

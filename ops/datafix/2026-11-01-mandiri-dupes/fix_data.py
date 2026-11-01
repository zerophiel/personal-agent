"""Data fix for the Mandiri October e-statement recorded on 1 Nov 18:23 WIB: 17 of its rows, dated 5-24 Oct, are bank rows
the 1-26 Oct mutation file of the same account already holds, read with other wording, so the old record_mutations stored
them a second time (October outflow counted twice). Run by deploy.sh in the vault-tools container after the new code is
built, which matches such rows by date and amount, so a re-sent file cannot bring them back. Checks first, one backup,
then the 17 rows go in one transaction, each logged in change_log with the whole row, and the file's new_rows drops to
what it really added. DRY = True does all of it on an in-memory copy. Safe to run again."""
import os, sqlite3, sys
sys.path.insert(0, "/app")
from vault_tools import changelog
from vault_tools.ledger import connect

DRY = False
DB, BAK = "/data/ledger.db", "/data/ledger.db.bak-pre-mandiri-dupes"
ALIAS, EARLIER, ESTATEMENT = "mandiri-utama", ("2026-10-01", "2026-10-26"), ("2026-10-01", "2026-10-31")
IDS = tuple(range(2449, 2466))      # the e-statement's rows dated inside the earlier file (the 1 Nov probe)
TOLERANCE = 3                       # Rp of cents rounding, as mutations.ROUNDING_TOLERANCE
WHY = ("baris ganda: e-statement Mandiri Oktober membaca ulang transaksi yang sudah tercatat dari mutasi 1-26 Okt "
       "(#{twin}) dengan tulisan lain")


def files(conn):
    acct = conn.execute("SELECT id FROM accounts WHERE alias=?", (ALIAS,)).fetchone()["id"]
    by = {(r["period_start"], r["period_end"]): r for r in conn.execute("SELECT * FROM mutation_files WHERE account_id=?", (acct,))}
    return acct, by[EARLIER], by[ESTATEMENT]


def gap(conn, acct, f, minus=0):
    held = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account_id=? AND source='mutation'"
                        " AND txn_date BETWEEN ? AND ?", (acct, f["period_start"], f["period_end"])).fetchone()[0]
    return held - minus - (f["closing_balance"] - f["opening_balance"])


def plan(conn):
    """[(row, twin id)] to remove, or [] when already done. Stops on anything unexpected."""
    acct, a, b = files(conn)
    rows = conn.execute(f"SELECT * FROM transactions WHERE id IN ({','.join('?' * len(IDS))}) ORDER BY id", IDS).fetchall()
    stored = conn.execute("SELECT COUNT(*) FROM transactions WHERE file_hash=?", (b["file_hash"],)).fetchone()[0]
    if not rows:
        assert stored == b["new_rows"] == b["row_count"] - (a["row_count"]), (stored, b["new_rows"])
        return []
    assert len(rows) == len(IDS), f"STOP: only {len(rows)} of the {len(IDS)} rows are there; look before writing"
    assert stored == b["new_rows"], f"STOP: the e-statement holds {stored} rows, its file says {b['new_rows']}"
    inside = {r["id"] for r in conn.execute("SELECT id FROM transactions WHERE file_hash=? AND txn_date <= ?",
                                            (b["file_hash"], EARLIER[1]))}
    assert inside == set(IDS), f"STOP: the e-statement rows dated inside the earlier file are {sorted(inside)}"
    out, taken = [], set()
    for r in rows:
        assert (r["file_hash"], r["account_id"], r["source"]) == (b["file_hash"], acct, "mutation"), f"STOP: #{r['id']} moved"
        assert r["category"] is None and r["merged_into"] is None, f"STOP: #{r['id']} was categorized or merged since"
        refs = conn.execute("SELECT COUNT(*) FROM transactions WHERE merged_into=?", (r["id"],)).fetchone()[0]
        assert refs == 0, f"STOP: a receipt points at #{r['id']}"
        twin = next((t["id"] for t in conn.execute("SELECT id FROM transactions WHERE file_hash=? AND txn_date=? AND amount=?"
                                                   " ORDER BY id", (a["file_hash"], r["txn_date"], r["amount"]))
                     if t["id"] not in taken), None)
        assert twin is not None, f"STOP: #{r['id']} has no row of the same day and amount in the earlier file"
        taken.add(twin)
        out.append((r, twin))
    total = sum(r["amount"] for r, _ in out)
    # the fix is exactly what makes both files agree with the ledger again
    assert abs(gap(conn, acct, a, total)) <= TOLERANCE and abs(gap(conn, acct, b, total)) <= TOLERANCE, \
        (gap(conn, acct, a, total), gap(conn, acct, b, total))
    return out


def show(conn, label):
    acct, a, b = files(conn)
    n = conn.execute("SELECT COUNT(*) FROM transactions WHERE file_hash=?", (b["file_hash"],)).fetchone()[0]
    print(f"{label}: earlier file gap {gap(conn, acct, a)} | e-statement gap {gap(conn, acct, b)} | e-statement rows {n},"
          f" new_rows {b['new_rows']}")


# 1. read only: what goes, checked
ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ro.row_factory = sqlite3.Row
todo = plan(ro)
show(ro, "now")
if not todo:
    print("already done: the rows are gone and the file's new_rows matches")
    sys.exit(0)
print("to remove", len(todo), "rows, total", sum(r["amount"] for r, _ in todo), "| twins", [t for _, t in todo])

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

# 3. one transaction: re-checked on the target, each row logged whole, then removed; the file's count follows
todo = plan(conn)
acct, a, b = files(conn)
for r, twin in todo:
    changelog.log(conn, "transactions", r["id"], "hapus", dict(r), None, WHY.format(twin=twin))
    conn.execute("DELETE FROM transactions WHERE id=?", (r["id"],))
changelog.log(conn, "mutation_files", b["file_hash"], "ubah", {"new_rows": b["new_rows"]}, {"new_rows": b["new_rows"] - len(todo)},
              f"{len(todo)} baris ganda dihapus (transaksi 5-24 Okt yang sudah ada dari mutasi 1-26 Okt)")
conn.execute("UPDATE mutation_files SET new_rows=? WHERE file_hash=?", (b["new_rows"] - len(todo), b["file_hash"]))
conn.commit()
show(conn, "after")
print("change_log rows written:", conn.execute("SELECT COUNT(*) FROM change_log WHERE reason LIKE 'baris ganda%'"
                                               " OR reason LIKE '% baris ganda dihapus%'").fetchone()[0])
